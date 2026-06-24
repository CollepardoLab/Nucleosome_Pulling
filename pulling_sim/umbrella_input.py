#Generate umbrella in.nucl_1..5
from __future__ import annotations
from pathlib import Path

_DATA_DIR = Path(__file__).parent / "data"


def _extract_bond_coefficients(log_path: Path) -> list[str]:
    coeffs = []
    for line in log_path.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("bond_coeff"):
            parts = stripped.split()
            if int(parts[1]) >= 4:
                coeffs.append(stripped)
    if not coeffs:
        raise ValueError(
            f"No sequence-specific bond_coeff in {log_path}.\n"
            "Check setup stage SLURM job has been completed."
        )
    return coeffs


def generate_umbrella_inputs(sim_dir: Path, histone: str) -> None:
    template_path = _DATA_DIR / histone / "in.nucl_umbrella"
    if not template_path.exists():
        raise FileNotFoundError(
            f"Umbrella template not found for '{histone}'.\n"
            f"Expected: {template_path}"
        )
    template = template_path.read_text()

    log_path = sim_dir / "setup_stage" / "log.nucl_1.txt"
    if not log_path.exists():
        raise FileNotFoundError(
            f"Setup log not found: {log_path}\n"
            "Run the setup_stage SLURM job first."
        )

    bond_coeff_lines = _extract_bond_coefficients(log_path)
    bond_block = "\n".join(bond_coeff_lines)

    for replica in range(1, 6):
        content = template.replace("###BOND_COEFFICIENTS###", bond_block)
        content = content.replace("###R###", str(replica))
        (sim_dir / f"in.nucl_{replica}").write_text(content)

    print(f"Generated in.nucl_1..5 in {sim_dir} "
          f"({len(bond_coeff_lines)} sequence-specific bond coefficients).")
