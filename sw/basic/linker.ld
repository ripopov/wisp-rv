OUTPUT_ARCH(riscv)
ENTRY(_start)

SECTIONS {
    . = 0x80000000;

    .text : ALIGN(4) {
        *(.text.init)
        *(.text*)
    }

    .rodata : ALIGN(8) {
        *(.rodata*)
    }

    .data : ALIGN(8) {
        *(.data*)
    }

    .bss : ALIGN(8) {
        __bss_start = .;
        *(.sbss*)
        *(.bss*)
        *(COMMON)
        __bss_end = .;
    }

    .tohost : ALIGN(8) {
        *(.tohost)
    }

    . = ALIGN(16);
    . = . + 4096;
    _stack_top = .;
}
