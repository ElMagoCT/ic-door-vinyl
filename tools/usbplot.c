// usbplot - talk to the Graphtec CE6000 Plus over USB with nothing but IOKit (no driver, no libusb).
// The cutter is a USB printer-class device: one bulk OUT pipe (commands in) and one bulk IN pipe
// (replies out). Build:  clang -O2 -framework IOKit -framework CoreFoundation -o usbplot usbplot.c
//   usbplot info                 show the pipes
//   usbplot query 'OI;' [ms]     send a command, print what comes back (default 2000 ms wait)
//   usbplot send FILE.plt        stream a job; blocks while the cutter drains its buffer
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <CoreFoundation/CoreFoundation.h>
#include <IOKit/IOKitLib.h>
#include <IOKit/IOCFPlugIn.h>
#include <IOKit/usb/IOUSBLib.h>
#include <IOKit/usb/USB.h>

#define VID 0x0b4d   /* GRAPHTEC */
#define PID 0x1130   /* CE6000Plus */
typedef IOUSBInterfaceInterface190 Intf;

static int prop_int(io_service_t s, const char *key) {
    CFStringRef k = CFStringCreateWithCString(NULL, key, kCFStringEncodingUTF8);
    CFTypeRef v = IORegistryEntryCreateCFProperty(s, k, kCFAllocatorDefault, 0);
    CFRelease(k);
    int r = -1;
    if (v && CFGetTypeID(v) == CFNumberGetTypeID()) CFNumberGetValue(v, kCFNumberIntType, &r);
    if (v) CFRelease(v);
    return r;
}

static Intf **open_intf(void) {
    io_iterator_t it = 0;
    if (IOServiceGetMatchingServices(kIOMainPortDefault, IOServiceMatching("IOUSBHostInterface"), &it) != KERN_SUCCESS) return NULL;
    io_service_t svc, found = 0;
    while ((svc = IOIteratorNext(it))) {
        if (prop_int(svc, "idVendor") == VID && prop_int(svc, "idProduct") == PID && prop_int(svc, "bInterfaceNumber") == 0) { found = svc; break; }
        IOObjectRelease(svc);
    }
    IOObjectRelease(it);
    if (!found) { fprintf(stderr, "usbplot: no Graphtec CE6000 Plus on USB. Is it switched on and plugged in?\n"); return NULL; }
    IOCFPlugInInterface **plug = NULL; SInt32 score = 0;
    kern_return_t kr = IOCreatePlugInInterfaceForService(found, kIOUSBInterfaceUserClientTypeID, kIOCFPlugInInterfaceID, &plug, &score);
    IOObjectRelease(found);
    if (kr != KERN_SUCCESS || !plug) { fprintf(stderr, "usbplot: IOCreatePlugInInterfaceForService failed: 0x%x\n", kr); return NULL; }
    Intf **intf = NULL;
    HRESULT hr = (*plug)->QueryInterface(plug, CFUUIDGetUUIDBytes(kIOUSBInterfaceInterfaceID190), (LPVOID *)&intf);
    (*plug)->Release(plug);
    if (hr || !intf) { fprintf(stderr, "usbplot: QueryInterface failed\n"); return NULL; }
    kr = (*intf)->USBInterfaceOpen(intf);
    if (kr == kIOReturnExclusiveAccess) kr = (*intf)->USBInterfaceOpenSeize(intf);
    if (kr != KERN_SUCCESS) { fprintf(stderr, "usbplot: cannot open the cutter's USB interface: 0x%x (does another program have it open?)\n", kr); (*intf)->Release(intf); return NULL; }
    return intf;
}

static int find_pipes(Intf **intf, UInt8 *in, UInt8 *out, int verbose) {
    UInt8 n = 0; (*intf)->GetNumEndpoints(intf, &n);
    *in = *out = 0;
    for (UInt8 p = 1; p <= n; p++) {
        UInt8 dir, num, type, interval; UInt16 maxp;
        if ((*intf)->GetPipeProperties(intf, p, &dir, &num, &type, &maxp, &interval) != KERN_SUCCESS) continue;
        if (verbose) printf("pipe %d: endpoint %d %s type %d maxpacket %d\n", p, num, dir == kUSBIn ? "IN " : "OUT", type, maxp);
        if (type == kUSBBulk) { if (dir == kUSBIn && !*in) *in = p; if (dir == kUSBOut && !*out) *out = p; }
    }
    return *out != 0;
}

/* read until nothing arrives for `ms`; returns bytes read, prints them when print!=0 */
static long drain(Intf **intf, UInt8 pin, int ms, int print) {
    char buf[4096]; long total = 0; int wait = ms;
    if (!pin) return 0;
    for (;;) {
        UInt32 sz = sizeof buf;
        kern_return_t kr = (*intf)->ReadPipeTO(intf, pin, buf, &sz, wait, wait);
        if (kr == KERN_SUCCESS && sz > 0) { if (print) fwrite(buf, 1, sz, stdout); total += sz; wait = 300; continue; }
        /* a timeout is not a stall: clearing the pipe here would reset the host's data toggle and the
           device's next reply packet would be silently dropped (every other query went unanswered) */
        if (kr == kIOUSBPipeStalled) (*intf)->ClearPipeStallBothEnds(intf, pin);
        break;
    }
    if (print && total) { fputs("\n", stdout); fflush(stdout); }
    return total;
}

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: usbplot info | query 'CMD;' [ms] | send FILE\n"); return 1; }
    Intf **intf = open_intf();
    if (!intf) return 2;
    UInt8 pin, pout;
    int verbose = !strcmp(argv[1], "info");
    if (!find_pipes(intf, &pin, &pout, verbose)) { fprintf(stderr, "usbplot: no bulk OUT pipe\n"); return 3; }
    int rc = 0;
    if (verbose) {
        printf("bulk OUT pipe %d, bulk IN pipe %d\n", pout, pin);
    } else if (!strcmp(argv[1], "query") && argc >= 3) {
        int ms = argc >= 4 ? atoi(argv[3]) : 2000;
        kern_return_t kr = (*intf)->WritePipeTO(intf, pout, argv[2], (UInt32)strlen(argv[2]), 5000, 5000);
        if (kr != KERN_SUCCESS) { fprintf(stderr, "usbplot: write failed: 0x%x\n", kr); rc = 4; }
        else if (!drain(intf, pin, ms, 1)) { fprintf(stderr, "(no reply within %d ms)\n", ms); rc = 5; }
    } else if (!strcmp(argv[1], "send") && argc >= 3) {
        FILE *f = fopen(argv[2], "rb");
        if (!f) { perror(argv[2]); rc = 1; }
        else {
            fseek(f, 0, SEEK_END); long size = ftell(f); fseek(f, 0, SEEK_SET);
            static char buf[16384]; long done = 0; size_t n;
            while ((n = fread(buf, 1, sizeof buf, f)) > 0) {
                kern_return_t kr = (*intf)->WritePipeTO(intf, pout, buf, (UInt32)n, 0, 0);
                if (kr != KERN_SUCCESS) { fprintf(stderr, "\nusbplot: write failed after %ld bytes: 0x%x\n", done, kr); rc = 4; break; }
                done += n;
                fprintf(stderr, "\r  sent %ld / %ld bytes (%.0f%%)", done, size, 100.0 * done / size); fflush(stderr);
            }
            fclose(f);
            fprintf(stderr, "\n");
            if (!rc) { long r = drain(intf, pin, 500, 1); if (r) fprintf(stderr, "(the cutter sent %ld bytes back, shown above)\n", r); }
        }
    } else { fprintf(stderr, "usage: usbplot info | query 'CMD;' [ms] | send FILE\n"); rc = 1; }
    (*intf)->USBInterfaceClose(intf);
    (*intf)->Release(intf);
    return rc;
}
