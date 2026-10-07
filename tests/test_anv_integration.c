#define _GNU_SOURCE
#include <assert.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include "anv_gpu_reclaim.h"

enum { INTEL_KMD_TYPE_XE = 1 };
struct intel_device_info {
   bool has_local_mem;
   int kmd_type;
   struct { struct { struct { uint64_t free, size; } mappable; } sram; } mem;
};
struct anv_physical_device {
   struct intel_device_info info;
   struct { uint64_t available; } sys;
   bool experimental_gpu_reclaim_budget_logged;
};
static bool enabled, diagnostic, query_ok = true;
static unsigned queries, reads;
static const char *snapshot = "MemAvailable: 10 kB\nGPUReclaim: 20 kB\n";
static bool debug_get_bool_option(const char *key, bool fallback)
{
   (void)fallback;
   return strcmp(key, "ANV_EXPERIMENTAL_GPU_RECLAIM") == 0 ? enabled : diagnostic;
}
static bool intel_device_info_xe_query_regions(int fd, struct intel_device_info *raw, bool update)
{
   (void)fd; (void)update;
   queries++;
   raw->mem.sram.mappable.free = 25 * 1024;
   raw->mem.sram.mappable.size = 100 * 1024;
   return query_ok;
}
static int fake_open(const char *path, int flags)
{
   (void)flags;
   assert(strcmp(path, "/proc/meminfo") == 0);
   return 3;
}
static ssize_t fake_read(int fd, void *buffer, size_t count)
{
   (void)fd;
   reads++;
   assert(count > strlen(snapshot));
   memcpy(buffer, snapshot, strlen(snapshot));
   return strlen(snapshot);
}
static int fake_close(int fd) { (void)fd; return 0; }
#define open fake_open
#define read fake_read
#define close fake_close
#include "anv_reclaim_integration.h"

int main(void)
{
   struct anv_physical_device device = { .info.kmd_type = INTEL_KMD_TYPE_XE,
                                        .sys.available = 10 * 1024 };
   anv_apply_gpu_reclaim(&device, 7);
   assert(queries == 0 && reads == 0 && device.sys.available == 10 * 1024);
   enabled = true;
   anv_apply_gpu_reclaim(&device, 7);
   assert(queries == 1 && reads == 1 && device.sys.available == 25 * 1024);
   device.sys.available = 10 * 1024;
   query_ok = false;
   anv_apply_gpu_reclaim(&device, 7);
   assert(device.sys.available == 10 * 1024);
   query_ok = true;
   snapshot = "MemAvailable: 10 kB\nGPUReclaim: bad kB\n";
   anv_apply_gpu_reclaim(&device, 7);
   assert(device.sys.available == 10 * 1024);
   snapshot = "MemAvailable: 10 kB\nGPUReclaim: 20 kB\n";
   enabled = false; diagnostic = true;
   anv_apply_gpu_reclaim(&device, 7);
   assert(device.sys.available == 10 * 1024); /* Off-switch diagnostics are observational. */
   enabled = true; diagnostic = false;
   device.info.has_local_mem = true;
   unsigned before = queries;
   anv_apply_gpu_reclaim(&device, 7);
   assert(queries == before && device.sys.available == 10 * 1024);
   device.info.has_local_mem = false; device.info.kmd_type = 0;
   anv_apply_gpu_reclaim(&device, 7);
   assert(queries == before);
   puts("ANV opt-in integration and conservative-fallback tests passed");
   return 0;
}
