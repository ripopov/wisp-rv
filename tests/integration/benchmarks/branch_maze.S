.section .text
.globl _start

_start:
    addi x1, x0, 0
    addi x2, x0, 0
    addi x3, x0, 400

branch_loop:
    andi x4, x1, 3
    beq x4, x0, add_1

    addi x5, x0, 1
    beq x4, x5, add_3

    addi x5, x0, 2
    beq x4, x5, add_5

add_7:
    addi x2, x2, 7
    jal x0, branch_continue

add_5:
    addi x2, x2, 5
    jal x0, branch_continue

add_3:
    addi x2, x2, 3
    jal x0, branch_continue

add_1:
    addi x2, x2, 1

branch_continue:
    addi x1, x1, 1
    addi x3, x3, -1
    bne x3, x0, branch_loop

    sd x2, 0x418(x0)

    addi x31, x0, 1
    sd x31, 0x200(x0)

done:
    jal x0, done
