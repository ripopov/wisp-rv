from __future__ import annotations

import argparse
import shlex
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .toolchain import Rv64Toolchain, require_rv64_toolchain

DEFAULT_MARCH = "rv64im_zicsr"
DEFAULT_MABI = "lp64"


@dataclass(frozen=True)
class ProgramBuildArtifacts:
    source: Path
    linker_script: Path
    elf_path: Path
    map_path: Path
    dump_path: Path
    bin_path: Path


def _run_checked(cmd: Sequence[str], *, step: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        rendered = shlex.join(cmd)
        raise RuntimeError(
            f"RV64 build step failed: {step}\n"
            f"command: {rendered}\n"
            f"stdout:\n{exc.stdout}\n"
            f"stderr:\n{exc.stderr}"
        ) from exc


def build_rv64_program(
    source: Path,
    linker_script: Path,
    output_dir: Path,
    *,
    march: str = DEFAULT_MARCH,
    mabi: str = DEFAULT_MABI,
    extra_gcc_flags: Sequence[str] = (),
    toolchain: Rv64Toolchain | None = None,
) -> ProgramBuildArtifacts:
    tc = toolchain or require_rv64_toolchain()

    source = Path(source).resolve()
    linker_script = Path(linker_script).resolve()
    output_dir = Path(output_dir).resolve()

    if not source.exists():
        raise FileNotFoundError(f"Program source not found: {source}")
    if not linker_script.exists():
        raise FileNotFoundError(f"Linker script not found: {linker_script}")

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = source.stem

    elf_path = output_dir / f"{stem}.elf"
    map_path = output_dir / f"{stem}.map"
    dump_path = output_dir / f"{stem}.dump"
    bin_path = output_dir / f"{stem}.bin"

    gcc_cmd = [
        tc.gcc,
        f"-march={march}",
        f"-mabi={mabi}",
        "-ffreestanding",
        "-nostdlib",
        "-nostartfiles",
        "-T",
        str(linker_script),
        f"-Wl,-Map,{map_path}",
        "-o",
        str(elf_path),
        *extra_gcc_flags,
        str(source),
    ]
    _run_checked(gcc_cmd, step="gcc compile/link")

    objcopy_cmd = [
        tc.objcopy,
        "-O",
        "binary",
        str(elf_path),
        str(bin_path),
    ]
    _run_checked(objcopy_cmd, step="objcopy binary export")

    objdump_cmd = [
        tc.objdump,
        "-d",
        "-M",
        "no-aliases",
        str(elf_path),
    ]
    disasm = _run_checked(objdump_cmd, step="objdump disassembly")
    dump_path.write_text(disasm.stdout)

    return ProgramBuildArtifacts(
        source=source,
        linker_script=linker_script,
        elf_path=elf_path,
        map_path=map_path,
        dump_path=dump_path,
        bin_path=bin_path,
    )


def bin_to_u32_words(bin_path: Path) -> dict[int, int]:
    data = Path(bin_path).read_bytes()
    words: dict[int, int] = {}
    for idx in range(0, len(data), 4):
        chunk = data[idx : idx + 4]
        words[idx // 4] = int.from_bytes(chunk.ljust(4, b"\x00"), "little")
    return words


def build_rv64_program_u32_words(
    source: Path,
    linker_script: Path,
    *,
    march: str = DEFAULT_MARCH,
    mabi: str = DEFAULT_MABI,
    extra_gcc_flags: Sequence[str] = (),
    toolchain: Rv64Toolchain | None = None,
) -> dict[int, int]:
    with tempfile.TemporaryDirectory(
        prefix=f"wisp-rv64-{Path(source).stem}-"
    ) as tmpdir:
        artifacts = build_rv64_program(
            source=source,
            linker_script=linker_script,
            output_dir=Path(tmpdir),
            march=march,
            mabi=mabi,
            extra_gcc_flags=extra_gcc_flags,
            toolchain=toolchain,
        )
        return bin_to_u32_words(artifacts.bin_path)


def _main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a bare-metal RV64 program for integration tests."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("--linker", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--march", default=DEFAULT_MARCH)
    parser.add_argument("--mabi", default=DEFAULT_MABI)
    parser.add_argument("--extra-gcc-flag", action="append", default=[])
    args = parser.parse_args()

    artifacts = build_rv64_program(
        source=args.source,
        linker_script=args.linker,
        output_dir=args.out_dir,
        march=args.march,
        mabi=args.mabi,
        extra_gcc_flags=tuple(args.extra_gcc_flag),
    )

    print(f"elf: {artifacts.elf_path}")
    print(f"map: {artifacts.map_path}")
    print(f"dump: {artifacts.dump_path}")
    print(f"bin: {artifacts.bin_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
