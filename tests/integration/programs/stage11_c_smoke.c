typedef unsigned long u64;

extern u64 _stack_top;

__attribute__((noreturn))
void _start(void)
{
    volatile u64 *const tohost = (volatile u64 *)0x200;
    volatile u64 *const scratch = (volatile u64 *)0x238;

    __asm__ volatile("la sp, _stack_top");

    u64 sum = 0;
    for (u64 i = 1; i <= 5; ++i) {
        sum += i;
    }

    scratch[0] = sum;
    tohost[0] = 1;

    while (1) {
        __asm__ volatile("nop");
    }
}
