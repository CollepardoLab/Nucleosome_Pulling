from __future__ import annotations
from pathlib import Path

_COMPLEMENT = str.maketrans("ATCG", "TAGC")

_DATA_DIR = Path(__file__).parent / "data"


def _read_atom_ids(histone: str) -> list[int]:
    number_file = _DATA_DIR / histone / "number.txt"
    if not number_file.exists():
        raise FileNotFoundError(
            f"numbering file not found for histone '{histone}'.\n"
            f"expected: {number_file}"
        )
    ids = [int(line.strip()) for line in number_file.read_text().splitlines() if line.strip()]
    return ids

# 211 bp sequence (exact 211)
def generate_dna_sequence_txt(dna: str, histone: str, out_path: Path) -> None:
    dna = dna.upper()
    complement = dna.translate(_COMPLEMENT)

    atom_ids = _read_atom_ids(histone)
    if len(atom_ids) != len(dna):
        raise ValueError(
            f"Ellipsoid numbering for '{histone}' has {len(atom_ids)} entries "
            f"but DNA has {len(dna)} bases."
        )

    lines = [f"# {len(dna)}"]
    for atom_id, base, comp in zip(atom_ids, dna, complement):
        lines.append(f"{atom_id} {base}{comp}")

    out_path.write_text("\n".join(lines) + "\n")
