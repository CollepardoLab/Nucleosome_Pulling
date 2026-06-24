from __future__ import annotations
import subprocess
from pathlib import Path

import numpy as np


def build_meta_files(
    sim_dir: Path,
    n_windows: int = 60,
    n_replicas: int = 5,
    lo: float = 25.0,
    hi: float = 725.0,
    k: float = 0.025,
) -> tuple[list[int], list[int]]:
    v0s = np.linspace(lo, hi, n_windows)
    combined: list[str] = []
    per_rep: dict[int, list[str]] = {i: [] for i in range(1, n_replicas + 1)}
    windows_ok: list[int] = []
    windows_missing: list[int] = []

    for w, v0 in zip(range(1, n_windows + 1), v0s):
        wdir = sim_dir / str(w)
        trajs = [wdir / f"out_{i}.colvars.traj" for i in range(1, n_replicas + 1)]
        existing = [t for t in trajs if t.exists()]

        if not existing:
            windows_missing.append(w)
            continue

        windows_ok.append(w)

        # Concatenate all replicas into cvs.txt for this window
        cvs_path = wdir / "cvs.txt"
        with open(cvs_path, "w") as fh:
            for t in existing:
                fh.write(t.read_text())

        combined.append(f"{cvs_path} {v0} {k}\n")

        for i in range(1, n_replicas + 1):
            t = wdir / f"out_{i}.colvars.traj"
            if t.exists():
                per_rep[i].append(f"{t} {v0} {k}\n")

    (sim_dir / "meta_file.txt").write_text("".join(combined))
    for i in range(1, n_replicas + 1):
        if per_rep[i]:
            (sim_dir / f"meta_file{i}.txt").write_text("".join(per_rep[i]))

    return windows_ok, windows_missing


def run_wham(
    sim_dir: Path,
    wham_exe: Path,
    lo: float = 25.0,
    hi_wham: float = 720.0,
    bins: int = 200,
    tol: float = 0.00001,
    temp: float = 300.0,
    n_replicas: int = 5,
) -> None:
    base_args = f"{lo} {hi_wham} {bins} {tol} {temp} 0"

    def _wham(meta: str, out: str) -> int:
        cmd = f"{wham_exe} {base_args} {meta} {out}"
        result = subprocess.run(cmd, shell=True, cwd=sim_dir)
        return result.returncode

    rc = _wham("meta_file.txt", "pmf.txt")
    if rc != 0:
        raise RuntimeError(f"WHAM failed (exit {rc}) for combined PMF.")

    for i in range(1, n_replicas + 1):
        meta = sim_dir / f"meta_file{i}.txt"
        if meta.exists():
            rc = _wham(f"meta_file{i}.txt", f"pmf{i}.txt")
            if rc != 0:
                raise RuntimeError(f"WHAM failed (exit {rc}) for replica {i}.")
