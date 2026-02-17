.section .text
.globl _start

_start:
    # Arithmetic chain.
    addi x1, x0, 10
    addi x2, x0, 20
    add x3, x1, x2
    sd x3, 0x300(x0)

    sub x4, x3, x1
    sd x4, 0x308(x0)

    # RAW hazard chain.
    addi x5, x0, 7
    addi x6, x5, 3
    addi x7, x6, 4
    sd x7, 0x310(x0)

    # Branch taken and wrong-path suppression marker.
    addi x8, x0, 5
    addi x9, x0, 5
    beq x8, x9, branch_taken
    addi x10, x0, 99
    sd x10, 0x338(x0)

branch_taken:
    addi x10, x0, 1
    sd x10, 0x318(x0)

    # JAL path and wrong-path suppression marker.
    jal x0, after_jump
    addi x12, x0, 99
    sd x12, 0x330(x0)

after_jump:
    addi x12, x0, 77
    sd x12, 0x320(x0)
    addi x13, x0, 42
    sd x13, 0x328(x0)

    # Memory write-width checks.
    addi x14, x0, 0x55
    sd x14, 0x340(x0)
    addi x15, x0, 0x22
    sb x15, 0x348(x0)
    sh x14, 0x34a(x0)
    sw x14, 0x350(x0)
    sd x14, 0x358(x0)

    # Completion marker.
    addi x30, x0, 1
    sd x30, 0x200(x0)

done:
    jal x0, done
