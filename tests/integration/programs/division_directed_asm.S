.section .text
.globl _start

_start:
    la sp, _stack_top

    # Result buffer base address: 0x7080.
    li t0, 0x7080

    # Case 0 (signed 64-bit): a=100, b=7 -> q=14, r=2.
    li t1, 100
    li t2, 7
    div t3, t1, t2
    rem t4, t1, t2
    sd t3, 0(t0)
    sd t4, 8(t0)

    # Case 1 (unsigned 64-bit): a=0xffffffffffffffff, b=3
    # -> q=0x5555555555555555, r=0.
    li t1, -1
    li t2, 3
    divu t3, t1, t2
    remu t4, t1, t2
    sd t3, 16(t0)
    sd t4, 24(t0)

    # Case 2 (signed overflow): a=MIN_S64 (0x8000000000000000), b=-1
    # -> q=MIN_S64, r=0.
    li t1, 1
    slli t1, t1, 63
    li t2, -1
    div t3, t1, t2
    rem t4, t1, t2
    sd t3, 32(t0)
    sd t4, 40(t0)

    # Case 3 (signed divide-by-zero): a=77, b=0 -> q=-1, r=77.
    li t1, 77
    li t2, 0
    div t3, t1, t2
    rem t4, t1, t2
    sd t3, 48(t0)
    sd t4, 56(t0)

    # Case 4 (signed 32-bit): a=-9 (0xfffffff7), b=2 -> q=-4, r=-1.
    li t1, -9
    li t2, 2
    divw t3, t1, t2
    remw t4, t1, t2
    sd t3, 64(t0)
    sd t4, 72(t0)

    # Case 5 (unsigned 32-bit): a=0xfffffffe, b=3 -> q=0x55555554, r=2.
    li t1, 0xfffffffe
    li t2, 3
    divuw t3, t1, t2
    remuw t4, t1, t2
    sd t3, 80(t0)
    sd t4, 88(t0)

    # Case 6 (dependency chain):
    # dep_a=123456789012345, dep_b=97
    # dep_q1=1272750402189 (0x0000012855d5ea8d)
    # dep_q2=424250134063  (0x00000062c7474e2f)
    # dep_r2=8
    # mix = dep_q1 ^ (dep_q2 << 1) ^ (dep_r2 << 32)
    #     = 0x000001e5db5b76d3.
    li t1, 123456789012345
    li t2, 97
    div s0, t1, t2
    li t5, 3
    div s1, s0, t5
    li t5, 11
    rem s2, s1, t5
    sd s0, 96(t0)
    sd s1, 104(t0)
    sd s2, 112(t0)
    slli t5, s1, 1
    slli t6, s2, 32
    xor t5, s0, t5
    xor t5, t5, t6
    sd t5, 120(t0)

    # Case 7 (signed 32-bit overflow): a=MIN_S32 (0x80000000), b=-1
    # -> q=MIN_S32 sign-extended (0xffffffff80000000), r=0.
    li t1, 0x80000000
    li t2, -1
    divw t3, t1, t2
    remw t4, t1, t2
    sd t3, 128(t0)
    sd t4, 136(t0)

    # Completion marker at tohost address 0x7000.
    li t1, 0x7000
    li t2, 1
    sd t2, 0(t1)

done:
    jal x0, done
