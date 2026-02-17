from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

REQUIRED_TOOLCHAIN_BINARIES = (
    "riscv64-unknown-elf-gcc",
    "riscv64-unknown-elf-objcopy",
    "riscv64-unknown-elf-objdump",
)


@dataclass(frozen=True)
class Rv64Toolchain:
    gcc: str
    objcopy: str
    objdump: str
    gcc_version: str
    objcopy_version: str
    objdump_version: str


def find_missing_toolchain_binaries() -> list[str]:
    missing: list[str] = []
    for binary in REQUIRED_TOOLCHAIN_BINARIES:
        if shutil.which(binary) is None:
            missing.append(binary)
    return missing


def format_missing_toolchain_error(missing: list[str]) -> str:
    joined = ", ".join(missing)
    return (
        "Missing required RISC-V bare-metal toolchain binaries: "
        f"{joined}.\n"
        "Install the RISC-V GNU toolchain and ensure binaries are on PATH.\n"
        "macOS (Homebrew): brew install riscv-gnu-toolchain"
    )


def _read_tool_version(binary_path: str) -> str:
    result = subprocess.run(
        [binary_path, "--version"],
        check=True,
        capture_output=True,
        text=True,
    )
    first_line = result.stdout.splitlines()[0].strip() if result.stdout else ""
    return first_line or "version unavailable"


def discover_rv64_toolchain() -> Rv64Toolchain | None:
    missing = find_missing_toolchain_binaries()
    if missing:
        return None

    gcc = shutil.which("riscv64-unknown-elf-gcc")
    objcopy = shutil.which("riscv64-unknown-elf-objcopy")
    objdump = shutil.which("riscv64-unknown-elf-objdump")
    assert gcc is not None
    assert objcopy is not None
    assert objdump is not None

    try:
        return Rv64Toolchain(
            gcc=gcc,
            objcopy=objcopy,
            objdump=objdump,
            gcc_version=_read_tool_version(gcc),
            objcopy_version=_read_tool_version(objcopy),
            objdump_version=_read_tool_version(objdump),
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            "Failed to run RISC-V toolchain version command.\n"
            f"command: {' '.join(exc.cmd)}\n"
            f"stdout:\n{exc.stdout}\n"
            f"stderr:\n{exc.stderr}"
        ) from exc


def require_rv64_toolchain() -> Rv64Toolchain:
    toolchain = discover_rv64_toolchain()
    if toolchain is None:
        raise RuntimeError(
            format_missing_toolchain_error(find_missing_toolchain_binaries())
        )
    return toolchain
