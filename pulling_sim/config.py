from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml


@dataclass
class Archer2Config:
    account: str
    lmp: str
    chromatin_so: str
    ld_library_path: str
    partition: str = "standard"
    qos: str = "standard"
    wham: str = ""  # optional path to wham executable


@dataclass
class UserConfig:
    archer2: Archer2Config

    @classmethod
    def load(cls, path: Path) -> "UserConfig":
        with open(path) as f:
            data = yaml.safe_load(f)
        a = data["archer2"]
        return cls(
            archer2=Archer2Config(
                account=a["account"],
                lmp=a["lmp"],
                chromatin_so=a["chromatin_so"],
                ld_library_path=a["ld_library_path"],
                partition=a.get("partition", "standard"),
                qos=a.get("qos", "standard"),
                wham=a.get("wham", ""),
            ),
        )


@dataclass
class SequenceConfig:
    name: str
    dna: str  # raw 211-bp string


@dataclass
class AcetylationConfig:
    enabled: bool = False
    sites: dict = field(default_factory=dict)  # e.g. {"H3": [56], "H4": [77, 79]}


@dataclass
class JobConfig:
    nodes: int
    ntasks: int
    time: str


@dataclass
class SimConfig:
    histone: str
    sequence: SequenceConfig
    acetylation: AcetylationConfig
    job_setup: JobConfig
    job_umbrella: JobConfig

    @classmethod
    def load(cls, path: Path) -> "SimConfig":
        with open(path) as f:
            data = yaml.safe_load(f)

        seq = data["sequence"]
        acet = data.get("acetylation", {})
        js = data.get("job_setup", {})
        ju = data.get("job_umbrella", {})

        sim = cls(
            histone=data["histone"],
            sequence=SequenceConfig(name=seq["name"], dna=seq["dna"].replace(" ", "").upper()),
            acetylation=AcetylationConfig(
                enabled=acet.get("enabled", False),
                sites=acet.get("sites", {}),
            ),
            job_setup=JobConfig(
                nodes=js.get("nodes", 1),
                ntasks=js.get("ntasks", 128),
                time=js.get("time", "4:00:00"),
            ),
            job_umbrella=JobConfig(
                nodes=ju.get("nodes", 5),
                ntasks=ju.get("ntasks", 640),
                time=ju.get("time", "24:00:00"),
            ),
        )

        if len(sim.sequence.dna) != 211:
            raise ValueError(
                f"DNA sequence must be 211 bases, got {len(sim.sequence.dna)}."
            )
        if sim.acetylation.enabled and sim.histone != "1KX5":
            raise ValueError("Acetylation is only supported for the 1KX5 histone.")

        return sim
