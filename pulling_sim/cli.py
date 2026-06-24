from __future__ import annotations
import subprocess
import sys
from pathlib import Path

import click
import yaml

from .config import SimConfig, UserConfig
from .scaffold import build_simulation
from .analyse import build_meta_files, run_wham

DEFAULT_USER_CONFIG = Path.home() / ".pulling_sim" / "user_config.yaml"


@click.group()
def main():
    """pulling-sim: automate nucleosome pulling simulations on Archer2."""


# pulling-sim init

@main.command()
@click.option("--output", "-o", default=None, help="Path to write user_config.yaml")
def init(output):
    """Interactive setup: create user_config.yaml with your Archer2 paths."""
    out_path = Path(output) if output else DEFAULT_USER_CONFIG

    click.echo("Setting up your Archer2 configuration.")
    click.echo("These values are stored once and reused for every simulation.\n")

    account = click.prompt("SLURM account", default="e280-Collepardo")
    partition = click.prompt("SLURM partition", default="standard")
    qos = click.prompt("SLURM QOS", default="standard")
    lmp = click.prompt("Path to lmp binary on Archer2")
    chromatin_so = click.prompt("Path to chromatin.so on Archer2")
    ld_lib = click.prompt(
        "LD_LIBRARY_PATH",
        default="/work/y07/shared/utils/core/cmake/3.18.4/lib:"
                "/opt/cray/libfabric/1.12.1.2.2.0.0/lib64:"
                "/opt/cray/pe/gcc/11.2.0/snos/lib64",
    )
    wham = click.prompt("Path to wham executable on Archer2 (for PMF analysis)", default="")
    data = {
        "archer2": {
            "account": account,
            "partition": partition,
            "qos": qos,
            "lmp": lmp,
            "chromatin_so": chromatin_so,
            "ld_library_path": ld_lib,
            "wham": wham,
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)

    click.echo(f"\nConfiguration saved to {out_path}")
    click.echo("Run 'pulling-sim setup sim.yaml' to create a simulation.")


# pulling-sim setup

@main.command()
@click.argument("sim_yaml", type=click.Path(exists=True))
@click.option("--user-config", "-u", default=None, help="Path to user_config.yaml")
@click.option("--output-dir", "-d", default=".", show_default=True,
              help="Directory in which to create the simulation folder")
def setup(sim_yaml, user_config, output_dir):
    """Create a new simulation directory from SIM_YAML."""
    user_cfg_path = Path(user_config) if user_config else DEFAULT_USER_CONFIG
    if not user_cfg_path.exists():
        click.echo(
            f"User config not found at {user_cfg_path}. Run 'pulling-sim init' first.",
            err=True,
        )
        sys.exit(1)

    user_cfg = UserConfig.load(user_cfg_path)
    sim_cfg = SimConfig.load(Path(sim_yaml))

    sim_dir = build_simulation(sim_cfg, user_cfg, Path(output_dir), sim_yaml_src=Path(sim_yaml))

    click.echo(f"\nSimulation directory created: {sim_dir}")
    click.echo("\nTo launch the full workflow, run:")
    click.echo(f"  bash {sim_dir}/run_all.sh")
    click.echo("\nThis submits the setup job, which will automatically submit")
    click.echo("the umbrella job once pulling is complete.")


# pulling-sim post-pull

@main.command("post-pull")
@click.argument("sim_dir", type=click.Path(exists=True))
def post_pull(sim_dir):
    """Run post-pulling steps after the SLURM setup job completes.

    Runs inside setup_stage/: creates data_start_files_no_LH, extracts window
    snapshots, moves them to the parent, runs paste2.sh and setup60colvars.py.
    """
    sim_path = Path(sim_dir).resolve()
    stage = sim_path / "setup_stage"

    if not stage.is_dir():
        click.echo(f"setup_stage/ not found in {sim_path}", err=True)
        sys.exit(1)

    def run(cmd: str, cwd: Path) -> None:
        click.echo(f"  $ {cmd}")
        result = subprocess.run(cmd, shell=True, cwd=cwd)
        if result.returncode != 0:
            click.echo(f"Command failed (exit {result.returncode}): {cmd}", err=True)
            sys.exit(result.returncode)

    click.echo("\n[1/5] Creating data_start_files_no_LH and extracting window snapshots...")
    run("mkdir -p data_start_files_no_LH", stage)
    run("python window_setup_no_LH.py", stage)

    click.echo("\n[2/5] Moving data_start_files_no_LH to simulation root...")
    run("mv data_start_files_no_LH ../", stage)

    click.echo("\n[3/5] Generating umbrella in.nucl_1..5 from setup log...")
    run("python generate_umbrella_inputs.py", sim_path)

    click.echo("\n[4/5] Running paste2.sh to distribute files to window directories...")
    run("bash paste2.sh", sim_path)

    click.echo("\n[5/5] Generating colvars settings for all windows...")
    run("python setup60colvars.py", sim_path)

    click.echo(
        f"\nDone. Submit the umbrella run with:\n"
        f"  cd {sim_path} && sbatch slurm-umbrella"
    )


# pulling-sim analyse

@main.command("analyse")
@click.argument("sim_dir", type=click.Path(exists=True))
@click.option("--wham", "wham_path", default=None,
              help="Path to wham executable. Overrides user_config.yaml.")
@click.option("--user-config", "-u", default=None, help="Path to user_config.yaml")
@click.option("--windows", default=60, show_default=True, help="Number of umbrella windows")
@click.option("--replicas", default=5, show_default=True, help="Number of replicas per window")
@click.option("--lo", default=25.0, show_default=True, help="Lower bound of pulling coordinate (Å)")
@click.option("--hi-wham", default=720.0, show_default=True,
              help="Upper bound passed to WHAM (Å); slightly below simulation hi")
@click.option("--bins", default=200, show_default=True, help="Number of WHAM histogram bins")
@click.option("--tol", default=0.00001, show_default=True, help="WHAM convergence tolerance")
@click.option("--temp", default=300.0, show_default=True, help="Temperature (K)")
def analyse(sim_dir, wham_path, user_config, windows, replicas, lo, hi_wham, bins, tol, temp):
    sim_path = Path(sim_dir).resolve()

    # Resolve wham executable: CLI flag > user_config > error
    if wham_path is None:
        user_cfg_path = Path(user_config) if user_config else DEFAULT_USER_CONFIG
        if user_cfg_path.exists():
            user_cfg = UserConfig.load(user_cfg_path)
            wham_path = user_cfg.archer2.wham or None
    if not wham_path:
        click.echo(
            "wham executable not specified. Use --wham /path/to/wham or add\n"
            "  wham: /path/to/wham\nunder archer2: in user_config.yaml.",
            err=True,
        )
        sys.exit(1)

    wham_exe = Path(wham_path)
    if not wham_exe.exists():
        click.echo(f"wham executable not found: {wham_exe}", err=True)
        sys.exit(1)

    click.echo(f"\n[1/2] Building meta files for {windows} windows × {replicas} replicas...")
    ok, missing = build_meta_files(
        sim_path, n_windows=windows, n_replicas=replicas, lo=lo, hi=725.0, k=0.025
    )
    click.echo(f"  Windows with data: {len(ok)}")
    if missing:
        click.echo(f"  Windows missing colvars trajectories: {missing}", err=True)

    click.echo("\n[2/2] Running WHAM...")
    try:
        run_wham(
            sim_path,
            wham_exe=wham_exe,
            lo=lo,
            hi_wham=hi_wham,
            bins=bins,
            tol=tol,
            temp=temp,
            n_replicas=replicas,
        )
    except RuntimeError as e:
        click.echo(str(e), err=True)
        sys.exit(1)

    click.echo(f"\nDone. Results written to {sim_path}/pmf.txt (and pmf1..{replicas}.txt)")
