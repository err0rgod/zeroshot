import queue
import threading
import time
import tkinter as tk
from pathlib import Path
import cv2
from PIL import Image, ImageTk

# Global reference to overlay instance for external tool calls
activeOverlayInstance = None


class CameraOverlay:
    def __init__(self):
        self.currentMode = "full"  # "full" or "split"
        self.statusText = "[LISTENING]"
        self.transcriptText = "Speak a command..."
        self.actionText = "System ready."

        self.root = None
        self.videoLabel = None
        self.statusLabel = None
        self.transcriptLabel = None
        self.actionLabel = None

        self.cap = None
        self.isRunning = False

        # Thread-safe queues for cross-thread GUI updates
        self.hudQueue = queue.Queue()
        self.modeQueue = queue.Queue()

    def initializeUi(self):
        """Construct the Tkinter window and HUD elements."""
        self.root = tk.Tk()
        self.root.title("Voice Action Camera Overlay")
        self.root.configure(bg="#0f111a")
        self.root.wm_attributes("-topmost", True)

        self.screenWidth = self.root.winfo_screenwidth()
        self.screenHeight = self.root.winfo_screenheight()

        # Video container
        self.videoContainer = tk.Frame(self.root, bg="#0f111a")
        self.videoContainer.pack(fill=tk.BOTH, expand=True)

        self.videoLabel = tk.Label(self.videoContainer, bg="#000000")
        self.videoLabel.pack(fill=tk.BOTH, expand=True)

        # Bottom HUD Panel (3 live metric lines)
        self.hudPanel = tk.Frame(self.root, bg="#161925", padx=10, pady=6)
        self.hudPanel.pack(fill=tk.X, side=tk.BOTTOM)

        self.statusLabel = tk.Label(
            self.hudPanel,
            text=f"STATUS: {self.statusText}",
            font=("Consolas", 10, "bold"),
            fg="#00e676",
            bg="#161925",
            anchor="w",
        )
        self.statusLabel.pack(fill=tk.X)

        self.transcriptLabel = tk.Label(
            self.hudPanel,
            text=f"TRANSCRIPT: {self.transcriptText}",
            font=("Segoe UI", 9),
            fg="#ffffff",
            bg="#161925",
            anchor="w",
        )
        self.transcriptLabel.pack(fill=tk.X)

        self.actionLabel = tk.Label(
            self.hudPanel,
            text=f"ACTION: {self.actionText}",
            font=("Segoe UI", 9, "italic"),
            fg="#00e5ff",
            bg="#161925",
            anchor="w",
        )
        self.actionLabel.pack(fill=tk.X)

        # Apply initial geometry
        self.applyModeGeometry()

        # Bind manual hotkey toggle: press 's' on the window to toggle split/full
        self.root.bind("<Key-s>", lambda event: self.toggleMode())
        self.root.bind("<Key-S>", lambda event: self.toggleMode())

        # Start camera capture with HD resolution request
        self.cap = cv2.VideoCapture(0)
        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.isRunning = True

        # Kick off render loop
        self.updateFrame()

    def cropAndResizeToCover(self, frame, targetW, targetH):
        """
        Preserve aspect ratio by center-cropping the video frame to match target dimensions.
        Completely eliminates stretching, squishing, and distortion.
        """
        frameH, frameW = frame.shape[:2]
        targetRatio = targetW / targetH
        frameRatio = frameW / frameH

        if frameRatio > targetRatio:
            # Source is wider than target: crop left & right margins
            newW = int(frameH * targetRatio)
            startX = (frameW - newW) // 2
            cropped = frame[:, startX:startX + newW]
        else:
            # Source is taller than target: crop top & bottom margins
            newH = int(frameW / targetRatio)
            startY = (frameH - newH) // 2
            cropped = frame[startY:startY + newH, :]

        return cv2.resize(cropped, (targetW, targetH), interpolation=cv2.INTER_LINEAR)

    def applyModeGeometry(self):
        """Update window geometry and position based on current mode."""
        if self.currentMode == "full":
            # Fullscreen intro mode: covers full screen
            self.root.geometry(f"{self.screenWidth}x{self.screenHeight}+0+0")
        else:
            # Split PiP mode: docked in bottom-right corner
            pipWidth = 420
            pipHeight = 320
            posX = self.screenWidth - pipWidth - 25
            posY = self.screenHeight - pipHeight - 65
            self.root.geometry(f"{pipWidth}x{pipHeight}+{posX}+{posY}")

    def toggleMode(self, targetMode=None):
        """Thread-safe request to toggle between 'full' and 'split' mode."""
        self.modeQueue.put(targetMode or "toggle")

    def updateHud(self, status=None, transcript=None, action=None):
        """Thread-safe request to update the 3-line HUD metrics via queue."""
        self.hudQueue.put({
            "status": status,
            "transcript": transcript,
            "action": action,
        })

    def processPendingGuiUpdates(self):
        """Process all queued thread-safe commands inside the Tkinter UI loop."""
        # 1. Process mode changes
        while not self.modeQueue.empty():
            try:
                target = self.modeQueue.get_nowait()
                if target == "toggle":
                    self.currentMode = "split" if self.currentMode == "full" else "full"
                else:
                    self.currentMode = target
                self.applyModeGeometry()
                print(f"[CAMERA OVERLAY] View mode switched to: {self.currentMode.upper()}")
            except queue.Empty:
                break

        # 2. Process HUD metric updates
        while not self.hudQueue.empty():
            try:
                update = self.hudQueue.get_nowait()
                status = update.get("status")
                transcript = update.get("transcript")
                action = update.get("action")

                if status is not None:
                    self.statusText = status
                    color = "#00e676"  # green
                    if "RECORDING" in status:
                        color = "#ff1744"  # red
                    elif "PROCESSING" in status or "ROUTING" in status:
                        color = "#ffd600"  # yellow
                    self.statusLabel.config(text=f"STATUS: {status}", fg=color)

                if transcript is not None:
                    self.transcriptText = transcript
                    display = transcript if len(transcript) <= 65 else transcript[:62] + "..."
                    self.transcriptLabel.config(text=f"TRANSCRIPT: \"{display}\"")

                if action is not None:
                    self.actionText = action
                    display = action if len(action) <= 65 else action[:62] + "..."
                    self.actionLabel.config(text=f"ACTION: {display}")

            except queue.Empty:
                break

    def updateFrame(self):
        """Capture webcam frame and render to Tkinter canvas with aspect-ratio preservation."""
        if not self.isRunning:
            return

        # Handle any pending thread-safe GUI updates
        self.processPendingGuiUpdates()

        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                # Mirror horizontally for natural webcam mirror feel
                frame = cv2.flip(frame, 1)

                # Determine optimized render dimensions (960x540 uses 4x less CPU than 1080p)
                if self.currentMode == "full":
                    targetW = 960
                    targetH = 540
                else:
                    targetW = 420
                    targetH = 235

                # Aspect-ratio preserved center-crop & resize
                fittedFrame = self.cropAndResizeToCover(frame, targetW, targetH)

                rgb = cv2.cvtColor(fittedFrame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb)
                imgTk = ImageTk.PhotoImage(image=img)

                self.videoLabel.imgTk = imgTk
                self.videoLabel.configure(image=imgTk)

        # Schedule next frame in ~42ms (~24 FPS) to keep CPU load below 3%
        if self.root and self.isRunning:
            self.root.after(42, self.updateFrame)

    def start(self):
        """Start the Tkinter event loop."""
        self.initializeUi()
        self.root.mainloop()
        self.cleanup()

    def cleanup(self):
        """Release camera hardware resources."""
        self.isRunning = False
        if self.cap and self.cap.isOpened():
            self.cap.release()


def startCameraOverlayThread():
    """Boot camera overlay in a dedicated background daemon thread."""
    global activeOverlayInstance
    activeOverlayInstance = CameraOverlay()

    cameraThread = threading.Thread(target=activeOverlayInstance.start, daemon=True)
    cameraThread.start()
    return activeOverlayInstance


def getCameraOverlay() -> CameraOverlay:
    """Retrieve active overlay instance."""
    global activeOverlayInstance
    return activeOverlayInstance


def updateCameraHud(status=None, transcript=None, action=None):
    """Global helper to update camera HUD from anywhere in pipeline."""
    global activeOverlayInstance
    if activeOverlayInstance:
        activeOverlayInstance.updateHud(status=status, transcript=transcript, action=action)


def toggleCameraView(mode: str = "split") -> str:
    """Voice tool to switch camera view between 'split' (bottom-right PiP) and 'full' (fullscreen)."""
    global activeOverlayInstance
    if activeOverlayInstance:
        target = "split" if "split" in mode.lower() else "full"
        activeOverlayInstance.toggleMode(target)
        return f"[SUCCESS] Switched camera to {target.upper()} mode."
    return "[NOTICE] Camera overlay is not running."


if __name__ == "__main__":
    overlay = CameraOverlay()
    overlay.start()
