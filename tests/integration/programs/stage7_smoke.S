.section .text
.globl _start

_start:
    # Bring-up NOP to avoid reset/fetch edge sensitivity.
    nop

    # EX/MEM forwarding.
    addi x1, x0, 5
    addi x2, x1, 10
    sd x2, 0x100(x0)

    # MEM/WB forwarding.
    addi x3, x0, 7
    addi x4, x0, 1
    addi x5, x3, 9
    sd x5, 0x108(x0)

    # EX/MEM priority over MEM/WB.
    addi x6, x0, 5
    addi x6, x0, 7
    addi x7, x6, 10
    sd x7, 0x110(x0)

    # x0 must never receive forwarded data.
    addi x0, x0, 5
    addi x8, x0, 10
    sd x8, 0x118(x0)

    # Store-data forwarding and load-use hazard stalling.
    addi x9, x0, 0x44
    sd x9, 0x120(x0)
    ld x10, 0x120(x0)
    addi x11, x10, 1
    sd x11, 0x128(x0)

    # Branch with forwarded operands + wrong-path flush.
    addi x12, x0, 5
    addi x13, x0, 5
    beq x12, x13, branch_taken
    addi x14, x0, 99
    sd x14, 0x158(x0)

branch_taken:
    addi x14, x0, 42
    sd x14, 0x130(x0)

    # AUIPC + JALR with forwarded base + wrong-path flush.
auipc_site:
    auipc x20, 0
    addi x20, x20, 20
jalr_site:
    jalr x21, x20, 0
    addi x22, x0, 0xde
    sd x22, 0x150(x0)

jalr_target:
    addi x22, x0, 0x33
    sd x22, 0x138(x0)
    sd x21, 0x140(x0)

    # LUI + ADDI constant build with forwarding.
    lui x23, 0x12345
    addi x23, x23, 0x678
    sd x23, 0x148(x0)

    # Signal completion via tohost.
    addi x24, x0, 0x200
    addi x25, x0, 1
    sd x25, 0(x24)

done:
    jal x0, done
