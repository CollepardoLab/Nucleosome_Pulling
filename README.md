# pulling-sim

CLI package for setting up and running nucleosome pulling simulations. Designed for Archer2, but adaptable to other HPC systems by modifying the bundled SLURM submission scripts.

---
## Requirements

- Collepardo Lab Chromatin model: General installation guide and requirements available: https://github.com/CollepardoLab/CollepardoLab_Chromatin_Model
- Python (version 3.9 at least)
- WHAM executable (Grossfield Lab): https://github.com/agrossfield/wham

## LAMMPS + Collepardo Lab Chromatin Model installation on Archer2 (Tested February 2026):
```bash
module load gcc/11.2.0
module load load-epcc-module
module load cmake/3.18.4
module load PrgEnv-gnu
git clone https://github.com/lammps/lammps.git
cd lammps/
git checkout tags/stable_29Sep2021 -b stable
mkdir build && cd build
cmake -D BUILD_SHARED_LIBS=yes -D BUILD_TOOLS=yes -D PKG_ASPHERE=yes -D PKG_RIGID=yes -D PKG_MOLECULE=yes -D PKG_PLUGIN=yes -D PKG_EXTRA-PAIR=yes -D PKG_COLVARS=yes -D PKG_EXTRA-FIX=yes -DCMAKE_CXX_FLAGS='-O3 -march=native -fno-math-errno -ffast-math' ../cmake
make install
cd ../
git clone https://github.com/CollepardoLab/CollepardoLab_Chromatin_Model.git
cd CollepardoLab_Chromatin_Model/
mkdir build && cd build
cmake -DLAMMPS_HEADER_DIR=/work/project/project/user/lammps/src ../../CollepardoLab_Chromatin_Model/
make install
echo $LD_LIBRARY_PATH
```
Notes:
- Save the LD_LIBRARY_PATH since you nees to add ir in the pulling_sim init step
- Get the path of lmp executable and chromatin.so
- Install Grossfield Lab WHAM and get the path of the executable

## Installation

Run once, either locally or on Archer2:

```bash
git clone https://github.com/CollepardoLab/nucleosome_pulling-package.git
cd pulling_sim
module load cray-python # (Archer2)
pip install -e .
```

Verify it works:

```bash
pulling-sim --help
```

---

## One-time user setup

Each Archer2 user must configure their personal paths once. This stores your LAMMPS binary, `chromatin.so` plugin, and SLURM account so you never hardcode them again.

```bash
pulling-sim init
```

You will be prompted for:

| Prompt | Example value |
|---|---|
| SLURM account | `eXXX` |
| SLURM partition | `standard` |
| SLURM QOS | `standard` |
| Path to `lmp` binary | `/work/eXXX/eXXX/YOUR_USER/lammps/build/lmp` |
| Path to `chromatin.so` | `/work/eXXX/eXXX/YOUR_USER/lammps/lib/chromatin.so` |
| `LD_LIBRARY_PATH` | (pre-filled with standard Archer2 paths, press Enter to accept) |
| (nothing else needed — template files are bundled in the package) | |

Configuration is saved to `~/.pulling_sim/user_config.yaml`. You can edit it manually at any time or re-run `pulling-sim init` to overwrite it.

Template files (`in.nucl`, `nucl_no_LH.txt`, `NAFlex_params.txt`, etc.) are bundled inside the package — you do not need to point to any reference directory.

If you want to store the config in a shared location instead of your home directory:

```bash
pulling-sim init --output /path/to/shared/user_config.yaml
```

---

## Running Nucleosome Pulling Simulation

### Step 1 — Write config file

Create a YAML file (e.g. `my_sim.yaml`) describing your system. A full template is at `configs/sim_config.yaml.example`.

```yaml
histone: 1KX5   # available: 1KX5, CENPA, H2AZ, macroH2A (1KX5 is the code for the canonical nucleosome core)

sequence:
  name: TP53                  # used in the output directory name: 1KX5_TP53
  dna: ATCGATCG...            # 211-base sequence, 5'-> 3' sense strand only

acetylation:
  enabled: false              # For acetylation: true (only available for 1KX5)
  sites:
    H3: []                    # e.g. [56] for H3K56ac
    H4: []                    # e.g. [77, 79]
    H2A: []
    H2B: []

job_setup:                    # SLURM settings for the 5 short pulling simulations
  nodes: 1
  ntasks: 128
  time: "4:00:00"

job_umbrella:                 # SLURM settings for the 60-window umbrella run
  nodes: 5
  ntasks: 640
  time: "24:00:00"
```

**Notes on the DNA sequence:**
- Must be exactly 211 bases (5'→3', sense strand only — the complementary strand is generated automatically).
- Spaces and line breaks in the YAML value are ignored.
- The atom numbering is read automatically from the reference directory based on the histone type; you do not need to provide it.

**Notes on acetylation:**
- Only supported for `histone: 1KX5`.
- List the residue positions to acetylate per histone chain (H3, H4, H2A, H2B). Example: `H3: [56]` acetylates H3K56.
- Lysine (atom type 12) is changed to acetyl-lysine (atom type 43) in the `nucl_no_LH.txt` starting structure.

### Step 2 — Create the simulation directory

```bash
pulling-sim setup my_sim.yaml
```

This creates `./1KX5_TP53/` (or `{HISTONE}_{sequence.name}/`) containing:

```
1KX5_TP53/
├── run_all.sh              ← the only script you need to run
├── slurm                   ← setup pulling job (paths pre-filled)
├── slurm-umbrella          ← umbrella sampling job (paths pre-filled)
├── paste2.sh               ← distributes files to window directories
├── setup60colvars.py       ← generates colvars for all 60 windows
└── setup_stage/
    ├── in.nucl             ← LAMMPS input template
    ├── setup.sh            ← generates in.nucl_1..5 with random seeds
    ├── nucl_no_LH.txt      ← starting structure (acetylated if requested)
    ├── DNA_sequence.txt    ← generated from your 211-bp sequence
    ├── NAFlex_params.txt   ← DNA force-field parameters
    ├── window_setup_no_LH.py
    ├── chromatin.so        ← symlink to your compiled plugin
    └── lmp_archer2         ← symlink to your lmp binary
```

To place the simulation in a specific directory:

```bash
pulling-sim setup my_sim.yaml --output-dir /work/e280/e280-Collepardo/YOUR_USER/sims
```

To use a non-default user config:

```bash
pulling-sim setup my_sim.yaml --user-config /path/to/user_config.yaml
```

### Step 3 — Launch the workflow

Copy the simulation directory to Archer2 (or run `pulling-sim setup` directly there), then:

```bash
bash 1KX5_TP53/run_all.sh
```

That is all. Internally this does:

1. Runs `setup.sh` — generates 5 randomised LAMMPS input files (`in.nucl_1` … `in.nucl_5`).
2. Submits `slurm` — the setup job runs the 5 short pulling simulations in parallel.
3. **Automatically, when the setup job finishes:**
   - Extracts window snapshots (`window_setup_no_LH.py`).
   - Distributes files to the 60 window directories (`paste2.sh`).
   - Generates colvars settings for umbrella sampling (`setup60colvars.py`).
   - Submits `slurm-umbrella`.
4. `slurm-umbrella` runs all 60 × 5 = 300 umbrella simulations.

---

## If something goes wrong mid-workflow

If the setup SLURM job fails after the pulling simulations but before completing the post-pull steps, you can re-run those steps manually:

```bash
pulling-sim post-pull 1KX5_TP53/
```

Then submit the umbrella job yourself:

```bash
cd 1KX5_TP53 && sbatch slurm-umbrella
```

---
## Data Analysis

Get the Potential of Mean Force using WHAM
```bash
pulling-sim analyse 1KX5_TP53/
```
## Bundled histone data

Template files are stored inside the package at `pulling_sim/data/{HISTONE}/`. No external reference directory is needed.

 `1KX5` 
 `CENPA` 
 `H2AZ` 
 `macroH2A`

```bash
pip install -e .   # reinstall to pick up the new files
```
