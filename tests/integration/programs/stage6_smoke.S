.section .text
.globl _start

_start:
    # Arithmetic chain with Stage-06 hazard padding.
    nop
    addi x1, x0, 5
    nop
    nop
    nop
    addi x2, x1, 10
    nop
    nop
    nop
    sd x2, 0x100(x0)

    # Branch/flush behavior.
    beq x0, x0, branch_taken
    addi x14, x0, 99
    nop
    nop
    sd x14, 0x110(x0)

branch_taken:
    addi x5, x0, 42
    nop
    nop
    nop
    nop
    sd x5, 0x108(x0)

    # Store/load path.
    addi x6, x0, 0x55
    nop
    nop
    nop
    sd x6, 0x120(x0)
    nop
    nop
    nop
    ld x7, 0x120(x0)
    nop
    nop
    nop
    nop
    addi x7, x7, 1
    nop
    nop
    sd x7, 0x128(x0)

    # AUIPC + JALR pattern.
auipc_site:
    auipc x10, 0
    nop
    nop
    addi x10, x10, 32
    nop
    nop
    jalr x11, x10, 0
    addi x12, x0, 0xde

jalr_target:
    addi x12, x0, 0x33
    nop
    nop
    sd x12, 0x130(x0)
    sd x11, 0x138(x0)

    # LUI + ADDI constant build.
    lui x13, 0x12345
    nop
    nop
    nop
    addi x13, x13, 0x678
    nop
    nop
    nop
    sd x13, 0x140(x0)

    # Signal completion by writing to tohost.
    addi x8, x0, 0x200
    addi x9, x0, 1
    nop
    nop
    sd x9, 0(x8)

done:
    jal x0, done
