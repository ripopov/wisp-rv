.section .text
.globl _start

_start:
    addi x1, x0, 1
    addi x2, x0, 2
    addi x3, x0, 3
    addi x4, x0, 200

alu_loop:
    add x1, x1, x2
    xor x2, x2, x3
    add x3, x3, x1
    addi x4, x4, -1
    bne x4, x0, alu_loop

    sd x1, 0x400(x0)
    sd x2, 0x408(x0)
    sd x3, 0x410(x0)

    addi x31, x0, 1
    sd x31, 0x200(x0)

done:
    jal x0, done
