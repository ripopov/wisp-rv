typedef unsigned long u64;

extern u64 _stack_top;

__attribute__((noreturn))
void _start(void)
{
    volatile u64 *const tohost = (volatile u64 *)0x200;
    volatile u64 *const result = (volatile u64 *)0x430;
    volatile u64 *const buf = (volatile u64 *)0x680;

    __asm__ volatile("la sp, _stack_top");

    for (u64 i = 0; i < 32; ++i) {
        buf[i] = i * 3 + 1;
    }

    u64 crc = 0;
    for (u64 i = 0; i < 32; ++i) {
        u64 v = buf[i];
        v = (v << 2) ^ (crc >> 1) ^ i;
        crc = crc + v;
        buf[i] = v;
    }

    result[0] = crc;
    tohost[0] = 1;

    while (1) {
        __asm__ volatile("nop");
    }
}
