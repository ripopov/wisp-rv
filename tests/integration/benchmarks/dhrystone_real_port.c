typedef unsigned long u64;

#define TOHOST_DONE_MAGIC 0x00000000D15EA5E1UL

extern u64 _stack_top;

static unsigned char g_heap[1024];
static unsigned long g_heap_used = 0;

char *malloc(unsigned long size)
{
    unsigned long aligned = (size + 7UL) & ~7UL;
    if (g_heap_used + aligned > (unsigned long)sizeof(g_heap)) {
        return (char *)0;
    }

    char *ptr = (char *)&g_heap[g_heap_used];
    g_heap_used += aligned;
    return ptr;
}

char *strcpy(char *dst, const char *src)
{
    char *out = dst;
    while (*src != '\0') {
        *dst++ = *src++;
    }
    *dst = '\0';
    return out;
}

int strcmp(const char *lhs, const char *rhs)
{
    while (*lhs != '\0' && *lhs == *rhs) {
        lhs++;
        rhs++;
    }
    return ((unsigned char)*lhs) - ((unsigned char)*rhs);
}

int printf(const char *fmt, ...)
{
    (void)fmt;
    return 0;
}

int scanf(const char *fmt, ...)
{
    (void)fmt;
    return 0;
}

long time(long *out)
{
    static long tick = 100;
    tick += 3;
    if (out != 0) {
        *out = tick;
    }
    return tick;
}

#include "dhrystone_v21/dhry_1.c"
#include "dhrystone_v21/dhry_2.c"

__attribute__((used, noreturn))
void dhrystone_finish(void);

__attribute__((naked, noreturn, section(".text.start")))
void _start(void)
{
    __asm__ volatile(
        "la sp, _stack_top\n"
        "call main\n"
        "j dhrystone_finish\n");
}

__attribute__((used, noreturn))
void dhrystone_finish(void)
{
    volatile u64 *const tohost = (volatile u64 *)0x7000;
    volatile u64 *const result = (volatile u64 *)0x7040;

    result[0] = (u64)(unsigned)Int_Glob;
    result[1] = (u64)(unsigned)Bool_Glob;
    result[2] = (u64)(unsigned)(unsigned char)Ch_1_Glob;
    result[3] = (u64)(unsigned)(unsigned char)Ch_2_Glob;
    result[4] = (u64)(unsigned)Arr_1_Glob[8];
    result[5] = (u64)(unsigned)Arr_2_Glob[8][7];

    tohost[0] = TOHOST_DONE_MAGIC;

    while (1) {
        __asm__ volatile("nop");
    }
}
