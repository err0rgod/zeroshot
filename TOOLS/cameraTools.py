import winsound
from CAMERA.cameraOverlay import toggleCameraView as overlayToggleCameraView


def toggleCameraView(mode: str = "split") -> str:
    """Switch camera display view between 'split' (picture-in-picture in bottom-right corner) and 'full' (fullscreen camera view).
    Call when user says 'split', 'split screen', 'full screen', 'full camera', or 'toggle camera'.
    Args:
        mode: The requested view mode ('split' or 'full').
    """
    cleanMode = "split" if "split" in mode.lower() else "full"
    result = overlayToggleCameraView(cleanMode)
    winsound.MessageBeep(winsound.MB_OK)
    return result


cameraToolsList = [
    toggleCameraView,
]
