volatile unsigned long g_sum;

int main(void) {
    unsigned long acc = 0;

    for (unsigned long i = 1; i <= 10; ++i) {
        acc += i;
    }

    g_sum = acc;
    return (g_sum == 55UL) ? 0 : 1;
}
