.section .text
.globl _start

_start:
    addi x1, x0, 0x500
    addi x2, x0, 0x600
    addi x3, x0, 32
    addi x4, x0, 1

init_src:
    sd x4, 0(x1)
    addi x4, x4, 1
    addi x1, x1, 8
    addi x3, x3, -1
    bne x3, x0, init_src

    addi x1, x0, 0x500
    addi x2, x0, 0x600
    addi x3, x0, 32
    addi x6, x0, 0

copy_loop:
    ld x5, 0(x1)
    nop
    nop
    sd x5, 0(x2)
    add x6, x6, x5
    addi x1, x1, 8
    addi x2, x2, 8
    addi x3, x3, -1
    bne x3, x0, copy_loop

    sd x6, 0x420(x0)

    addi x31, x0, 1
    sd x31, 0x200(x0)

done:
    jal x0, done
