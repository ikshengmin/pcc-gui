/* SDK declaration oracle only; compiling this with Apple Clang is not PCC
 * ownership evidence and does not execute or render CoreGraphics. */
#include <CoreGraphics/CoreGraphics.h>
#include <stddef.h>
#include <stdint.h>

_Static_assert(sizeof(void *) == 8, "64-bit pointers required");
_Static_assert(sizeof(size_t) == 8, "64-bit size_t required");
_Static_assert(sizeof(CGFloat) == 8, "CGFloat must be f64");
_Static_assert(sizeof(CGPoint) == 16 && _Alignof(CGPoint) == 8, "CGPoint ABI");
_Static_assert(sizeof(CGRect) == 32 && _Alignof(CGRect) == 8, "CGRect ABI");
_Static_assert(offsetof(CGPoint, x) == 0 && offsetof(CGPoint, y) == 8, "CGPoint fields");
_Static_assert(offsetof(CGRect, origin) == 0 && offsetof(CGRect, size) == 16, "CGRect fields");
_Static_assert(sizeof(CGBitmapInfo) == 4, "bitmap info must be u32");
_Static_assert((kCGImageAlphaPremultipliedLast | kCGBitmapByteOrder32Big) == 16385, "RGBA8 bitmap flags");

typedef CGContextRef (*BitmapABI)(void *, size_t, size_t, size_t, size_t, CGColorSpaceRef, uint32_t);
typedef CGColorSpaceRef (*ColorCreateABI)(void);
typedef void (*ColorReleaseABI)(CGColorSpaceRef);
typedef void (*ContextReleaseABI)(CGContextRef);
typedef void (*FillColorABI)(CGContextRef, double, double, double, double);
typedef void (*FillRectABI)(CGContextRef, CGRect);
typedef void (*StrokeABI)(CGContextRef, const CGPoint *, size_t);
#define ABI_CHECK(fn, type) _Static_assert(__builtin_types_compatible_p(__typeof__(&(fn)), type), #fn " signature")
ABI_CHECK(CGBitmapContextCreate, BitmapABI);
ABI_CHECK(CGColorSpaceCreateDeviceRGB, ColorCreateABI);
ABI_CHECK(CGColorSpaceRelease, ColorReleaseABI);
ABI_CHECK(CGContextRelease, ContextReleaseABI);
ABI_CHECK(CGContextSetRGBFillColor, FillColorABI);
ABI_CHECK(CGContextFillRect, FillRectABI);
ABI_CHECK(CGContextStrokeLineSegments, StrokeABI);
