.section .text
.globl _start

_start:
    nop

    # Forwarding sanity check.
    addi x1, x0, 5
    addi x2, x1, 10
    sd x2, 0x100(x0)

    # Program mtvec.
    la x20, trap_handler
    csrrw x0, mtvec, x20

    # mstatus read/write semantics.
    addi x3, x0, 0x8
    csrrw x4, mstatus, x3
    sd x4, 0x108(x0)
    csrrs x5, mstatus, x0
    sd x5, 0x110(x0)
    csrrci x0, mstatus, 0x8
    csrrs x6, mstatus, x0
    sd x6, 0x118(x0)

    # CSRRS with rs1=x0 must not write.
    addi x7, x0, 0x80
    csrrw x0, mie, x7
    csrrs x8, mie, x0
    sd x8, 0x120(x0)
    csrrs x9, mie, x0
    sd x9, 0x128(x0)

illegal_site:
    .word 0x00000000

after_illegal:
    csrrs x10, mcause, x0
    sd x10, 0x130(x0)
    csrrs x11, mepc, x0
    sd x11, 0x138(x0)
    csrrs x12, mtval, x0
    sd x12, 0x140(x0)

ecall_site:
    ecall

after_ecall:
    csrrs x13, mcause, x0
    sd x13, 0x148(x0)
    csrrs x14, mepc, x0
    sd x14, 0x150(x0)
    csrrs x15, mtval, x0
    sd x15, 0x158(x0)
    csrrs x16, mscratch, x0
    sd x16, 0x160(x0)

    csrrs x17, mcycle, x0
    sd x17, 0x168(x0)
    csrrs x18, minstret, x0
    sd x18, 0x170(x0)

ro_write_site:
    csrrw x19, mvendorid, x1

after_ro_write:
    csrrs x20, mcause, x0
    sd x20, 0x178(x0)
    csrrs x21, mepc, x0
    sd x21, 0x180(x0)
    csrrs x22, mtval, x0
    sd x22, 0x188(x0)
    csrrs x23, mscratch, x0
    sd x23, 0x190(x0)

    # M-extension multiply checks.
    addi x28, x0, 6
    addi x29, x0, 7
    mul x30, x28, x29
    sd x30, 0x198(x0)

    addi x28, x0, -3
    addi x29, x0, 5
    mulh x30, x28, x29
    sd x30, 0x1a0(x0)
    mulhsu x30, x28, x29
    sd x30, 0x1a8(x0)

    addi x28, x0, -1
    addi x29, x0, 2
    mulhu x30, x28, x29
    sd x30, 0x1b0(x0)
    mulw x30, x28, x29
    sd x30, 0x1b8(x0)

    # M-extension divide/remainder checks.
    addi x28, x0, 100
    addi x29, x0, 7
    div x30, x28, x29
    sd x30, 0x1c0(x0)

    addi x29, x0, 0
    div x30, x28, x29
    sd x30, 0x1c8(x0)

    addi x28, x0, 1
    slli x28, x28, 63
    addi x29, x0, -1
    div x30, x28, x29
    sd x30, 0x1d0(x0)

    addi x28, x0, -1
    addi x29, x0, 3
    divu x30, x28, x29
    sd x30, 0x1d8(x0)

    addi x28, x0, -9
    addi x29, x0, 2
    rem x30, x28, x29
    sd x30, 0x1e0(x0)

    addi x28, x0, -1
    addi x29, x0, 3
    remu x30, x28, x29
    sd x30, 0x1e8(x0)

    addi x28, x0, -9
    addi x29, x0, 2
    divw x30, x28, x29
    sd x30, 0x1f0(x0)

    addi x28, x0, -2
    addi x29, x0, 3
    divuw x30, x28, x29
    sd x30, 0x1f8(x0)

    addi x29, x0, 0
    divuw x30, x28, x29
    sd x30, 0x210(x0)

    addi x28, x0, -9
    addi x29, x0, 2
    remw x30, x28, x29
    sd x30, 0x218(x0)

    addi x28, x0, -2
    addi x29, x0, 3
    remuw x30, x28, x29
    sd x30, 0x220(x0)

    addi x29, x0, 0
    remuw x30, x28, x29
    sd x30, 0x228(x0)

    # Divide-result dependency check.
    addi x28, x0, 100
    addi x29, x0, 7
    div x30, x28, x29
    addi x31, x30, 1
    sd x31, 0x230(x0)

    # Signal completion via tohost.
    addi x24, x0, 0x200
    addi x25, x0, 1
    sd x25, 0(x24)

done:
    jal x0, done

trap_handler:
    csrrs x26, mepc, x0
    addi x26, x26, 4
    csrrw x0, mepc, x26
    csrrs x27, mscratch, x0
    addi x27, x27, 1
    csrrw x0, mscratch, x27
    mret
