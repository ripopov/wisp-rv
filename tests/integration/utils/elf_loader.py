from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

ELF_MAGIC = b"\x7fELF"
ELF_CLASS_64 = 2
ELF_DATA_LITTLE = 1
PT_LOAD = 1


@dataclass(frozen=True)
class ElfSegment:
    vaddr: int
    data: bytes


@dataclass(frozen=True)
class ElfImage:
    path: Path
    entry_point: int
    segments: tuple[ElfSegment, ...]


def load_elf_image(elf_path: Path) -> ElfImage:
    path = Path(elf_path).resolve()
    raw = path.read_bytes()

    if len(raw) < 64:
        raise ValueError(f"ELF file too small: {path}")
    if raw[:4] != ELF_MAGIC:
        raise ValueError(f"Not an ELF file: {path}")
    if raw[4] != ELF_CLASS_64:
        raise ValueError(f"Unsupported ELF class (expected ELF64): {path}")
    if raw[5] != ELF_DATA_LITTLE:
        raise ValueError(f"Unsupported ELF endianness (expected little-endian): {path}")

    (
        _e_type,
        _e_machine,
        _e_version,
        e_entry,
        e_phoff,
        _e_shoff,
        _e_flags,
        _e_ehsize,
        e_phentsize,
        e_phnum,
        _e_shentsize,
        _e_shnum,
        _e_shstrndx,
    ) = struct.unpack_from("<HHIQQQIHHHHHH", raw, 16)

    if e_phoff == 0 or e_phnum == 0:
        raise ValueError(f"ELF has no program headers: {path}")
    if e_phentsize < 56:
        raise ValueError(f"Unexpected ELF program header size: {e_phentsize}")

    segments: list[ElfSegment] = []
    for idx in range(e_phnum):
        ph_off = e_phoff + idx * e_phentsize
        if ph_off + 56 > len(raw):
            raise ValueError(f"Program header {idx} out of range in {path}")

        (
            p_type,
            _p_flags,
            p_offset,
            p_vaddr,
            _p_paddr,
            p_filesz,
            p_memsz,
            _p_align,
        ) = struct.unpack_from("<IIQQQQQQ", raw, ph_off)

        if p_type != PT_LOAD or p_memsz == 0:
            continue

        if p_filesz > p_memsz:
            raise ValueError(f"Invalid PT_LOAD sizes in {path}: filesz > memsz")
        if p_offset + p_filesz > len(raw):
            raise ValueError(f"PT_LOAD segment {idx} data out of range in {path}")

        seg_file = raw[p_offset : p_offset + p_filesz]
        if p_memsz > p_filesz:
            seg_data = seg_file + (b"\x00" * (p_memsz - p_filesz))
        else:
            seg_data = seg_file

        segments.append(ElfSegment(vaddr=p_vaddr, data=seg_data))

    if not segments:
        raise ValueError(f"ELF contains no loadable segments: {path}")

    segments.sort(key=lambda s: s.vaddr)
    return ElfImage(path=path, entry_point=e_entry, segments=tuple(segments))


def elf_image_to_byte_map(image: ElfImage) -> dict[int, int]:
    mem: dict[int, int] = {}
    for segment in image.segments:
        base = segment.vaddr
        for idx, byte in enumerate(segment.data):
            mem[base + idx] = byte
    return mem


def elf_image_to_word_writes(image: ElfImage) -> dict[int, tuple[int, int]]:
    writes: dict[int, tuple[int, int]] = {}
    for segment in image.segments:
        base = segment.vaddr
        for idx, byte in enumerate(segment.data):
            addr = base + idx
            word_addr = addr & ~0x7
            byte_lane = addr & 0x7

            cur_data, cur_be = writes.get(word_addr, (0, 0))
            cur_data &= ~(0xFF << (8 * byte_lane))
            cur_data |= (byte & 0xFF) << (8 * byte_lane)
            cur_be |= 1 << byte_lane
            writes[word_addr] = (cur_data, cur_be)
    return writes
