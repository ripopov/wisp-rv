typedef unsigned long u64;

extern u64 _stack_top;

__attribute__((noreturn))
void _start(void)
{
    volatile u64 *const tohost = (volatile u64 *)0x200;
    volatile u64 *const result = (volatile u64 *)0x428;

    __asm__ volatile("la sp, _stack_top");

    u64 a = 1;
    u64 b = 2;
    u64 c = 3;

    for (u64 i = 0; i < 300; ++i) {
        a = a + ((b << 1) ^ i);
        b = b + (a >> 3) + c;
        c = c ^ (a + b + i);
    }

    result[0] = a ^ b ^ c;
    tohost[0] = 1;

    while (1) {
        __asm__ volatile("nop");
    }
}
