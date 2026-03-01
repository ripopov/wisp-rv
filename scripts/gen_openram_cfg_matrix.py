#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass(frozen=True)
class RamGeometry:
    word_size: int
    num_words: int

    @property
    def macro_name(self) -> str:
        return f"sram_data_{self.word_size}x{self.num_words}_1rw"

    @property
    def cfg_name(self) -> str:
        return f"cfg_data_{self.word_size}x{self.num_words}_1rw.py"


MATRIX = [
    RamGeometry(8, 64),
    RamGeometry(16, 64),
    RamGeometry(32, 64),
    RamGeometry(32, 128),
    RamGeometry(64, 128),
    RamGeometry(128, 256),
]


def render_cfg(geometry: RamGeometry) -> str:
    return f"""word_size = {geometry.word_size}
num_words = {geometry.num_words}

num_rw_ports = 1
num_r_ports = 0
num_w_ports = 0

tech_name = "freepdk45"
nominal_corner_only = True
process_corners = ["TT"]
supply_voltages = [1.0]
temperatures = [25]

route_supplies = False
check_lvsdrc = False
netlist_only = True
use_conda = False

output_name = "{geometry.macro_name}"
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate OpenRAM config files for Nangate45/FreePDK45 study matrix."
    )
    parser.add_argument(
        "--out-dir",
        required=True,
        help="Directory where OpenRAM cfg_*.py files will be generated.",
    )
    parser.add_argument(
        "--manifest-json",
        default="",
        help="Optional path to write JSON manifest for generated geometries.",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = []
    for geometry in MATRIX:
        cfg_path = out_dir / geometry.cfg_name
        cfg_path.write_text(render_cfg(geometry), encoding="utf-8")
        manifest.append(
            {
                **asdict(geometry),
                "macro_name": geometry.macro_name,
                "cfg_path": str(cfg_path),
            }
        )
        print(
            f"{geometry.macro_name}\t{cfg_path}\t{geometry.word_size}\t{geometry.num_words}"
        )

    if args.manifest_json:
        manifest_path = Path(args.manifest_json)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
