# Microphone authorization

`status.py` is a typed compiled consumer of the read-only microphone status
query. Replace `__BRIDGE__` in a private copy with the absolute path of the
canonical native bridge. The result is the calling application's AVFoundation
authorization state: not determined (0), restricted (1), denied (2), granted
(3), or an unrecognized future value (4).

`pcc_gui_media_microphone_ask(owner, &request)` is the explicit operation that
may ask the user for access. Call it on the UI thread with a dedicated session
lease from `pcc_gui_protocol_open`. The native provider requires a nonempty
`NSMicrophoneUsageDescription` in the calling application's bundle. The caller
owns packaging, signing, the choice to request access, and frame/origin policy.
See Apple's [status query](https://developer.apple.com/documentation/avfoundation/avcapturedevice/authorizationstatus%28for%3A%29),
[request API](https://developer.apple.com/documentation/avfoundation/avcapturedevice/requestaccess%28for%3Acompletionhandler%3A%29),
and [usage description](https://developer.apple.com/documentation/bundleresources/information-property-list/nsmicrophoneusagedescription).

An accepted ask returns an ordinary claimed protocol request. Use the existing
response peek/take API on the UI thread. A successful reply carries one body
byte, `0` or `1`, and no metadata. A native start failure, such as a missing
usage description, becomes terminal failure 4. If allocating the completion
byte hits the queue's resource bound, the request becomes terminal failure 6.
The first terminal transition wins, including synchronous provider completion.
The caller's source Promise and permission callback run in the caller's event
turn. `pcc_gui_protocol_cancel` and `pcc_gui_protocol_retire` invalidate queue
delivery; an outstanding OS request can finish later. Keep the bridge loaded
while the platform retains a native completion block.

The test observes real status only. Its asynchronous provider is injected and
never calls the OS request API. Building `tests/fixtures/native_media.m` with
`PCC_GUI_MEDIA_TEST_LIBRARY` exposes the same deterministic provider for a
generated-handler integration: `pcc_gui_test_media_status`,
`pcc_gui_test_media_ask`, `pcc_gui_test_media_finish` and
`pcc_gui_test_media_pending`. Finish delivers on its invoking thread, allowing
a worker to publish and the UI owner to take the result. These four functions
are fixture-only. Native queue/AVFoundation observations, installed PCC1 and
production Harness permission wiring have separate qualification.
