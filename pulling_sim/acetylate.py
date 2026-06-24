from __future__ import annotations
import re
from pathlib import Path
## 1KX5 (no LH) HISTONE CORE IDs
histone_ranges = {
    "H3":  [(195, 330), (682, 817)],
    "H4":  [(330, 432), (817, 1032)],
    "H2A": [(432, 560), (1032, 1047)],
    "H2B": [(560, 682), (1047, 1169)],
}

atoms_per_nuc = 1169


def _should_acetylate(atom_id: int, acetyl_sites: dict[str, list[int]]) -> bool:
    local_id = (atom_id - 1) % atoms_per_nuc + 1
    for histone, ranges in histone_ranges.items():
        for start, end in ranges:
            rel_pos = local_id - start + 1
            if 1 <= rel_pos <= (end - start + 1):
                if rel_pos in acetyl_sites.get(histone, []):
                    return True
    return False

#TAIL LYS: 12 modified by 43 // CORE LYS: 32 by 44 (SELECTED IDs HAVE TO BE ORIGINALLY A LYS)
def acetylate_file(input_path: Path, output_path: Path, acetyl_sites: dict[str, list[int]]) -> None:
    in_atoms = False
    lines_out = []

    with open(input_path) as f:
        for line in f:
            stripped = line.strip()

            # Update "N atom types" header so LAMMPS accepts the new type numbers.
            if re.match(r"^\d+\s+atom types$", stripped):
                current_n = int(stripped.split()[0])
                new_n = max(current_n, 44)
                line = line.replace(str(current_n), str(new_n), 1)
                lines_out.append(line)
                continue

            if stripped == "Atoms":
                in_atoms = True
                lines_out.append(line)
                continue
            if in_atoms and stripped == "":
                lines_out.append(line)
                continue
            if in_atoms:
                if not re.match(r"^\d+", stripped):
                    in_atoms = False
                    lines_out.append(line)
                    continue
                parts = stripped.split()
                atom_id = int(parts[0])
                atom_type = int(parts[1])
                if atom_type == 12 and _should_acetylate(atom_id, acetyl_sites):
                    parts[1] = "43"
                    line = " ".join(parts) + "\n"
                elif atom_type == 32 and _should_acetylate(atom_id, acetyl_sites):
                    parts[1] = "44"
                    line = " ".join(parts) + "\n"
            lines_out.append(line)

    output_path.write_text("".join(lines_out))
