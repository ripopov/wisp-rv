from __future__ import annotations

import sys
from pathlib import Path

import pytest

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from utils import toolchain
from utils.build_rv64_program import (
    DEFAULT_MABI,
    DEFAULT_MARCH,
    bin_to_u32_words,
    build_rv64_program,
)

PROGRAMS_DIR = THIS_DIR / "programs"
LINKER_SCRIPT = THIS_DIR / "linker" / "rv64.ld"


def _skip_if_toolchain_missing() -> None:
    missing = toolchain.find_missing_toolchain_binaries()
    if missing:
        pytest.skip(toolchain.format_missing_toolchain_error(missing))


def test_build_stage9_assembly_program(tmp_path: Path) -> None:
    _skip_if_toolchain_missing()

    artifacts = build_rv64_program(
        source=PROGRAMS_DIR / "stage9_smoke.S",
        linker_script=LINKER_SCRIPT,
        output_dir=tmp_path,
        march=DEFAULT_MARCH,
        mabi=DEFAULT_MABI,
    )

    assert artifacts.elf_path.exists()
    assert artifacts.map_path.exists()
    assert artifacts.dump_path.exists()
    assert artifacts.bin_path.exists()
    assert artifacts.elf_path.stat().st_size > 0
    assert artifacts.map_path.stat().st_size > 0
    assert artifacts.dump_path.stat().st_size > 0
    assert artifacts.bin_path.stat().st_size > 0

    words = bin_to_u32_words(artifacts.bin_path)
    assert words


def test_toolchain_discovery_reports_versions() -> None:
    _skip_if_toolchain_missing()

    tc = toolchain.require_rv64_toolchain()
    assert tc.gcc_version
    assert tc.objcopy_version
    assert tc.objdump_version


def test_build_stage11_c_program(tmp_path: Path) -> None:
    _skip_if_toolchain_missing()

    artifacts = build_rv64_program(
        source=PROGRAMS_DIR / "stage11_c_smoke.c",
        linker_script=LINKER_SCRIPT,
        output_dir=tmp_path,
        march=DEFAULT_MARCH,
        mabi=DEFAULT_MABI,
        extra_gcc_flags=("-O2",),
    )

    assert artifacts.elf_path.exists()
    assert artifacts.map_path.exists()
    assert artifacts.dump_path.exists()
    assert artifacts.bin_path.exists()
    assert "<_start>" in artifacts.dump_path.read_text()


def test_program_sources_do_not_include_prebuilt_binaries() -> None:
    disallowed_suffixes = {".elf", ".bin", ".map", ".dump", ".o"}
    prebuilt = sorted(
        str(path.relative_to(PROGRAMS_DIR))
        for path in PROGRAMS_DIR.rglob("*")
        if path.is_file() and path.suffix in disallowed_suffixes
    )
    assert not prebuilt, f"Found prebuilt integration artifacts: {prebuilt}"


def test_missing_toolchain_error_is_clear(monkeypatch: pytest.MonkeyPatch) -> None:
    real_which = toolchain.shutil.which

    def fake_which(binary: str):
        if binary == "riscv64-unknown-elf-gcc":
            return None
        return real_which(binary)

    monkeypatch.setattr(toolchain.shutil, "which", fake_which)

    with pytest.raises(RuntimeError) as excinfo:
        toolchain.require_rv64_toolchain()

    msg = str(excinfo.value)
    assert "riscv64-unknown-elf-gcc" in msg
    assert "Install the RISC-V GNU toolchain" in msg
