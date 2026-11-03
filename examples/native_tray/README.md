# Owned image and tray capabilities

The canonical bridge provides main-thread image and status-item leases. Straight
RGBA8 input is copied into owned sRGB backing with an explicit integer scale.
The path decoder copies a bounded file snapshot and admits one AppKit bitmap;
Electron multi-scale selection and the original Windows ICO branch are separate.
Public image keys can retire while a tray retains the native image.

A tray has its own bounded native click queue. Peek is non-consuming; acknowledge
the head before calling source code. Menu attachment preserves the canonical
menu delegate, item targets and event queue, and prevents release/reparenting or
application-menu installation while attached. Attachment does not set
NSStatusItem.menu: the caller explicitly starts popup after its source callback,
preserving control over click/menu ordering. Popup performs synchronous native
tracking, separate from production Electron asynchronous event integration.

Release disables actions and invalidates the public key first. During its owned
popup, release requests cancellation and defers native view/image detachment until
tracking returns. The item belongs to the application; closing a normal window
does not remove it. No source object or callback enters AppKit action state.

`lease.py` is a compiled consumer of the common unsafe C ABI. Replace __BRIDGE__
in a private copy with the canonical bridge path. Host IR emission, external
clang/AppKit native tests and installed PCC1 execution have separate acceptance.
