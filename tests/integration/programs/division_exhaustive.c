typedef unsigned long u64;
typedef long s64;
typedef unsigned int u32;
typedef int s32;

extern u64 _stack_top;

#define ARRAY_LEN(x) (sizeof(x) / sizeof((x)[0]))
#define MIN_S64 ((s64)0x8000000000000000ULL)
#define MIN_S32 ((s32)0x80000000U)

static inline u64 mix(u64 acc, u64 value)
{
    acc ^= value + 0x9E3779B97F4A7C15ULL + (acc << 6) + (acc >> 2);
    return acc;
}

static const s64 EDGE_S64[] = {
    0,
    1,
    -1,
    2,
    -2,
    7,
    -7,
    0x7FFFFFFFFFFFFFFFLL,
    (s64)0x8000000000000000ULL,
    0x4000000000000000LL,
    (s64)0xC000000000000000ULL,
    0x0123456789ABCDEFLL,
};

static const u64 EDGE_U64[] = {
    0ULL,
    1ULL,
    2ULL,
    3ULL,
    7ULL,
    8ULL,
    0xFFFFFFFFFFFFFFFFULL,
    0x8000000000000000ULL,
    0x7FFFFFFFFFFFFFFFULL,
    0x0000000100000000ULL,
    0x00000000FFFFFFFFULL,
    0x123456789ABCDEF0ULL,
};

static const s32 EDGE_S32[] = {
    0,
    1,
    -1,
    2,
    -2,
    7,
    -7,
    0x7FFFFFFF,
    (s32)0x80000000U,
    0x40000000,
    (s32)0xC0000000U,
    0x12345678,
};

__attribute__((noreturn))
void _start(void)
{
    volatile u64 *const tohost = (volatile u64 *)0x7000;
    volatile u64 *const out = (volatile u64 *)0x7040;

    __asm__ volatile("la sp, _stack_top");

    u64 h_div = 0x1111111111111111ULL;
    u64 h_divu = 0x2222222222222222ULL;
    u64 h_rem = 0x3333333333333333ULL;
    u64 h_remu = 0x4444444444444444ULL;
    u64 h_divw = 0x5555555555555555ULL;
    u64 h_divuw = 0x6666666666666666ULL;
    u64 h_remw = 0x7777777777777777ULL;
    u64 h_remuw = 0x8888888888888888ULL;

    u64 iter_count = 0;

    for (s64 a = -16; a < 16; ++a) {
        for (s64 b = -16; b < 16; ++b) {
            s64 q = 0;
            s64 r = 0;
            if (b == 0) {
                q = -1;
                r = a;
            } else if ((a == MIN_S64) && (b == -1)) {
                q = MIN_S64;
                r = 0;
            } else {
                q = a / b;
                r = a % b;
            }

            u64 ua = (u64)a;
            u64 ub = (u64)b;
            u64 qu = (ub == 0) ? 0xFFFFFFFFFFFFFFFFULL : (ua / ub);
            u64 ru = (ub == 0) ? ua : (ua % ub);

            s32 aw = (s32)a;
            s32 bw = (s32)b;

            s32 qw = 0;
            s32 rw = 0;
            if (bw == 0) {
                qw = -1;
                rw = aw;
            } else if ((aw == MIN_S32) && (bw == -1)) {
                qw = MIN_S32;
                rw = 0;
            } else {
                qw = aw / bw;
                rw = aw % bw;
            }

            u32 auw = (u32)aw;
            u32 buw = (u32)bw;
            u32 quw_bits = (buw == 0) ? 0xFFFFFFFFU : (auw / buw);
            u32 ruw_bits = (buw == 0) ? auw : (auw % buw);
            s32 quw = (s32)quw_bits;
            s32 ruw = (s32)ruw_bits;

            h_div = mix(h_div, (u64)q);
            h_divu = mix(h_divu, qu);
            h_rem = mix(h_rem, (u64)r);
            h_remu = mix(h_remu, ru);
            h_divw = mix(h_divw, (u64)(s64)qw);
            h_divuw = mix(h_divuw, (u64)(s64)quw);
            h_remw = mix(h_remw, (u64)(s64)rw);
            h_remuw = mix(h_remuw, (u64)(s64)ruw);

            iter_count += 1;
        }
    }

    for (u64 i = 0; i < ARRAY_LEN(EDGE_S64); ++i) {
        for (u64 j = 0; j < ARRAY_LEN(EDGE_S64); ++j) {
            s64 a = EDGE_S64[i];
            s64 b = EDGE_S64[j];

            s64 q = 0;
            s64 r = 0;
            if (b == 0) {
                q = -1;
                r = a;
            } else if ((a == MIN_S64) && (b == -1)) {
                q = MIN_S64;
                r = 0;
            } else {
                q = a / b;
                r = a % b;
            }

            h_div = mix(h_div, (u64)q);
            h_rem = mix(h_rem, (u64)r);
            iter_count += 1;
        }
    }

    for (u64 i = 0; i < ARRAY_LEN(EDGE_U64); ++i) {
        for (u64 j = 0; j < ARRAY_LEN(EDGE_U64); ++j) {
            u64 a = EDGE_U64[i];
            u64 b = EDGE_U64[j];
            u64 q = (b == 0) ? 0xFFFFFFFFFFFFFFFFULL : (a / b);
            u64 r = (b == 0) ? a : (a % b);

            h_divu = mix(h_divu, q);
            h_remu = mix(h_remu, r);
            iter_count += 1;
        }
    }

    for (u64 i = 0; i < ARRAY_LEN(EDGE_S32); ++i) {
        for (u64 j = 0; j < ARRAY_LEN(EDGE_S32); ++j) {
            s32 a = EDGE_S32[i];
            s32 b = EDGE_S32[j];

            s32 q = 0;
            s32 r = 0;
            if (b == 0) {
                q = -1;
                r = a;
            } else if ((a == MIN_S32) && (b == -1)) {
                q = MIN_S32;
                r = 0;
            } else {
                q = a / b;
                r = a % b;
            }

            u32 au = (u32)a;
            u32 bu = (u32)b;
            u32 qu_bits = (bu == 0) ? 0xFFFFFFFFU : (au / bu);
            u32 ru_bits = (bu == 0) ? au : (au % bu);
            s32 qu = (s32)qu_bits;
            s32 ru = (s32)ru_bits;

            h_divw = mix(h_divw, (u64)(s64)q);
            h_divuw = mix(h_divuw, (u64)(s64)qu);
            h_remw = mix(h_remw, (u64)(s64)r);
            h_remuw = mix(h_remuw, (u64)(s64)ru);

            iter_count += 1;
        }
    }

    out[0] = h_div;
    out[1] = h_divu;
    out[2] = h_rem;
    out[3] = h_remu;
    out[4] = h_divw;
    out[5] = h_divuw;
    out[6] = h_remw;
    out[7] = h_remuw;
    out[8] = iter_count;

    tohost[0] = 1;

    while (1) {
        __asm__ volatile("nop");
    }
}
