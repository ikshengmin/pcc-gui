#ifndef PCC_GUI_NATIVE_IMAGE_H
#define PCC_GUI_NATIVE_IMAGE_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
/* Main-thread leases. Straight RGBA8 is copied; rows may contain padding.
 * scale is an explicit integer 1..8; info returns pixel dimensions and scale.
 * Statuses follow menu: 0 success, 2 invalid/stale/thread, 3 UTF8,
 * 4 native failure, 6 resource limit. Empty images have zero dimensions. */
int64_t pcc_gui_native_image_empty(int64_t *out);
int64_t pcc_gui_native_image_rgba(const void *data,int64_t length,int64_t width,int64_t height,int64_t stride,int64_t scale,int64_t *out);
/* AppKit single bitmap decoder; absent/undecodable input becomes an empty image.
 * This does not select Electron's multi-scale/ICO representation policy. */
int64_t pcc_gui_native_image_path(const void *path,int64_t length,int64_t *out);
int64_t pcc_gui_native_image_info(int64_t key,int64_t *width,int64_t *height,int64_t *scale,int64_t *is_template);
int64_t pcc_gui_native_image_template(int64_t key,int64_t is_template);
int64_t pcc_gui_native_image_release(int64_t key);
int64_t pcc_gui_native_image_live_count(int64_t *out);
#ifdef __cplusplus
}
#endif
#endif
