#ifndef PCC_GUI_MEDIA_H
#define PCC_GUI_MEDIA_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

enum PccGuiMicrophoneStatus {
    PCC_GUI_MICROPHONE_NOT_DETERMINED = 0,
    PCC_GUI_MICROPHONE_RESTRICTED = 1,
    PCC_GUI_MICROPHONE_DENIED = 2,
    PCC_GUI_MICROPHONE_GRANTED = 3,
    PCC_GUI_MICROPHONE_UNKNOWN = 4
};

/* UI-thread access to the calling application's macOS microphone permission.
 * Reading status never requests access. The output is a PccGuiMicrophoneStatus.
 * Calls return 0 on success, 2 for invalid arguments or thread, and 4 if the
 * native provider is unavailable. */
int64_t pcc_gui_media_microphone_status(int64_t *out_status);

/* Use a dedicated pcc_gui_protocol_open lease for the session. This call
 * explicitly requests OS access and may present the application's native
 * prompt. The real provider requires an NSMicrophoneUsageDescription.
 * Success publishes a claimed protocol request key. A terminal reply has no
 * metadata and one body byte (0 denied, 1 granted). Provider failures use a
 * terminal failure with code 4 (or 6 for completion storage exhaustion).
 * Peek/take, cancel and retire through pcc_gui_protocol.h. They do not cancel
 * an OS prompt or change the OS permission. Late completions cannot publish
 * into a retired lease or a replacement session. No source callback runs in
 * the native completion. ABI statuses 2/4/5/6 preserve the output. An earlier
 * unclaimed FIFO request makes this operation busy without starting a prompt. */
int64_t pcc_gui_media_microphone_ask(int64_t owner, int64_t *out_request);

#ifdef __cplusplus
}
#endif
#endif
