#include "anv_gpu_reclaim.h"
#include <assert.h>
#include <stdio.h>

static void invalid(const char *text)
{
   uint64_t a = 17, r = 19;
   assert(!anv_gpu_reclaim_parse(text, &a, &r));
   assert(a == 17 && r == 19);
}

int main(void)
{
   uint64_t a, r, value;
   assert(anv_gpu_reclaim_parse("MemAvailable: 10 kB\nGPUActive: 999 kB\nGPUReclaim: 20 kB\n", &a, &r));
   assert(a == 10240 && r == 20480); /* GPUActive is not added. */
   assert(anv_gpu_reclaim_parse("GPUReclaim: 20 kB\nMemAvailable:\t10 kB\n", &a, &r));
   assert(a == 10240 && r == 20480);
   assert(anv_gpu_reclaim_parse("MemAvailable: 10 kB\n", &a, &r));
   assert(a == 10240 && r == 0);
   assert(anv_gpu_reclaim_parse("MemAvailable: 0 kB\nGPUReclaim: 0 kB\n", &a, &r));
   assert(a == 0 && r == 0);
   invalid("");
   invalid("GPUReclaim: 1 kB\n");
   invalid("MemAvailable: -1 kB\n");
   invalid("MemAvailable: +1 kB\n");
   invalid("MemAvailable: 1 MB\n");
   invalid("MemAvailable: 1kB\n");
   invalid("MemAvailable: 1 kBjunk\n");
   invalid("MemAvailable: 1 kB\nGPUReclaim: bad kB\n");
   invalid("MemAvailable: 1 kB\nGPUReclaim: 2 kB\nGPUReclaim: 3 kB\n");
   invalid("MemAvailable: 1 kB\nMemAvailable: 2 kB\n");
   invalid("MemAvailable: 18446744073709551616 kB\n"); /* decimal overflow */
   invalid("MemAvailable: 18014398509481984 kB\n"); /* byte overflow */
   invalid("MemAvailable: 18014398509481983 kB\nGPUReclaim: 1 kB\n"); /* sum overflow */
   invalid("MemAvailable: 1 kB"); /* truncated snapshot */
   assert(anv_gpu_reclaim_limit(100, 200, 1000, 1000, &value) && value == 300);
   assert(anv_gpu_reclaim_limit(100, 200, 250, 1000, &value) && value == 250);
   assert(anv_gpu_reclaim_limit(100, 0, 50, 1000, &value) && value == 50);
   value = 123;
   assert(!anv_gpu_reclaim_limit(UINT64_MAX, 1, UINT64_MAX, UINT64_MAX, &value));
   assert(value == 123);
   assert(!anv_gpu_reclaim_limit(100, 0, 1001, 1000, &value));
   assert(value == 123);
   puts("ANV parser and raw-region-limit tests passed");
   return 0;
}
