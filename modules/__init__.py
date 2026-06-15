"""SmartCart feature modules.

Exports are loaded lazily so importing one component does not initialize the
full computer-vision stack.
"""

_EXPORTS = {
    "BarcodeScanner": ("modules.barcode_scanner", "BarcodeScanner"),
    "PersonDetector": ("modules.person_detector", "PersonDetector"),
    "CustomerTracker": ("modules.customer_tracker", "CustomerTracker"),
    "SmartCart": ("modules.smart_cart", "SmartCart"),
    "Dashboard": ("modules.dashboard", "Dashboard"),
    "VideoHandler": ("modules.video_handler", "VideoHandler"),
    "VideoSource": ("modules.video_handler", "VideoSource"),
}

__all__ = sorted(_EXPORTS)


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = _EXPORTS[name]
    module = __import__(module_name, fromlist=[attr_name])
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
