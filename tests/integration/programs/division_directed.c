typedef unsigned long u64;
typedef long s64;
typedef unsigned int u32;
typedef int s32;

extern u64 _stack_top;

#define MIN_S64 ((s64)0x8000000000000000ULL)
#define MIN_S32 ((s32)0x80000000U)

__attribute__((noreturn))
void _start(void)
{
    volatile u64 *const tohost = (volatile u64 *)0x7000;
    volatile u64 *const out = (volatile u64 *)0x7080;

    __asm__ volatile("la sp, _stack_top");

    s64 a = 100;
    s64 b = 7;
    out[0] = (u64)(a / b);
    out[1] = (u64)(a % b);

    u64 ua = 0xFFFFFFFFFFFFFFFFULL;
    u64 ub = 3;
    out[2] = ua / ub;
    out[3] = ua % ub;

    s64 min64 = MIN_S64;
    s64 neg1 = -1;
    if ((min64 == MIN_S64) && (neg1 == -1)) {
        out[4] = (u64)MIN_S64;
        out[5] = 0;
    } else {
        out[4] = (u64)(min64 / neg1);
        out[5] = (u64)(min64 % neg1);
    }

    s64 znum = 77;
    s64 zden = 0;
    out[6] = (zden == 0) ? 0xFFFFFFFFFFFFFFFFULL : (u64)(znum / zden);
    out[7] = (zden == 0) ? (u64)znum : (u64)(znum % zden);

    s32 aw = -9;
    s32 bw = 2;
    s32 qsw = aw / bw;
    s32 rsw = aw % bw;
    out[8] = (u64)(s64)qsw;
    out[9] = (u64)(s64)rsw;

    u32 auw = 0xFFFFFFFEU;
    u32 buw = 3U;
    s32 quw = (s32)(auw / buw);
    s32 ruw = (s32)(auw % buw);
    out[10] = (u64)(s64)quw;
    out[11] = (u64)(s64)ruw;

    s64 dep_a = 123456789012345LL;
    s64 dep_b = 97;
    s64 dep_q1 = dep_a / dep_b;
    s64 dep_q2 = dep_q1 / 3;
    s64 dep_r2 = dep_q2 % 11;
    out[12] = (u64)dep_q1;
    out[13] = (u64)dep_q2;
    out[14] = (u64)dep_r2;
    out[15] = (u64)dep_q1 ^ ((u64)dep_q2 << 1) ^ ((u64)dep_r2 << 32);

    s32 min32 = MIN_S32;
    s32 m1 = -1;
    if ((min32 == MIN_S32) && (m1 == -1)) {
        out[16] = (u64)(s64)MIN_S32;
        out[17] = 0;
    } else {
        out[16] = (u64)(s64)(min32 / m1);
        out[17] = (u64)(s64)(min32 % m1);
    }

    tohost[0] = 1;

    while (1) {
        __asm__ volatile("nop");
    }
}
