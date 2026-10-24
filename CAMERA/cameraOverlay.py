import ctypes
import ctypes.wintypes as wt
import queue
import threading
import time
import tkinter as tk
from pathlib import Path
import cv2
from PIL import Image, ImageTk

# Global reference to overlay instance for external tool calls
activeOverlayInstance = None


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wt.LONG),
        ("top", wt.LONG),
        ("right", wt.LONG),
        ("bottom", wt.LONG),
    ]


def getScreenWorkArea():
    """Query usable desktop work area on Windows excluding taskbars."""
    try:
        rect = RECT()
        # SPI_GETWORKAREA = 0x0030
        res = ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)
        if res:
            return rect.left, rect.top, rect.right, rect.bottom
    except Exception:
        pass
    return None


class CameraOverlay:
    def __init__(self):
        self.currentMode = "full"  # "full" or "split"
        self.statusText = "[LISTENING]"
        self.transcriptText = "Speak a command..."
        self.actionText = "System ready."

        self.root = None
        self.videoContainer = None
        self.videoLabel = None
        self.hudPanel = None
        self.hudTopRow = None
        self.statusLabel = None
        self.toggleButton = None
        self.exitButton = None
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

        # Handle window close [X] cleanly
        self.root.protocol("WM_DELETE_WINDOW", self.onCloseWindow)

        self.screenWidth = self.root.winfo_screenwidth()
        self.screenHeight = self.root.winfo_screenheight()

        # Bottom HUD Panel (Packed FIRST with side=BOTTOM so it is NEVER pushed off screen)
        self.hudPanel = tk.Frame(
            self.root,
            bg="#131620",
            padx=14,
            pady=8,
            highlightthickness=1,
            highlightbackground="#252a3d",
            highlightcolor="#252a3d",
        )
        self.hudPanel.pack(fill=tk.X, side=tk.BOTTOM)

        # Top row of HUD: Status indicator on left, interactive controls on right
        self.hudTopRow = tk.Frame(self.hudPanel, bg="#131620")
        self.hudTopRow.pack(fill=tk.X, pady=(0, 2))

        self.statusLabel = tk.Label(
            self.hudTopRow,
            text=f"STATUS: {self.statusText}",
            font=("Consolas", 10, "bold"),
            fg="#00e676",
            bg="#131620",
            anchor="w",
        )
        self.statusLabel.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.exitButton = tk.Button(
            self.hudTopRow,
            text="Exit",
            font=("Segoe UI", 8, "bold"),
            fg="#ff5252",
            bg="#2a161f",
            activebackground="#ff1744",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=8,
            pady=1,
            cursor="hand2",
            command=self.onCloseWindow,
        )
        self.exitButton.pack(side=tk.RIGHT)

        self.toggleButton = tk.Button(
            self.hudTopRow,
            text="Split [S]",
            font=("Segoe UI", 8, "bold"),
            fg="#ffffff",
            bg="#252a3d",
            activebackground="#3b425f",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=8,
            pady=1,
            cursor="hand2",
            command=self.toggleMode,
        )
        self.toggleButton.pack(side=tk.RIGHT, padx=(0, 6))

        self.transcriptLabel = tk.Label(
            self.hudPanel,
            text=f"TRANSCRIPT: \"{self.transcriptText}\"",
            font=("Segoe UI", 9),
            fg="#e0e6ed",
            bg="#131620",
            anchor="w",
        )
        self.transcriptLabel.pack(fill=tk.X, pady=1)

        self.actionLabel = tk.Label(
            self.hudPanel,
            text=f"ACTION: {self.actionText}",
            font=("Segoe UI", 9, "italic"),
            fg="#00e5ff",
            bg="#131620",
            anchor="w",
        )
        self.actionLabel.pack(fill=tk.X, pady=1)

        # Video container (Packed SECOND with expand=True to claim remaining area above HUD)
        self.videoContainer = tk.Frame(self.root, bg="#000000")
        self.videoContainer.pack(fill=tk.BOTH, expand=True)

        self.videoLabel = tk.Label(self.videoContainer, bg="#000000")
        self.videoLabel.pack(fill=tk.BOTH, expand=True)

        # Apply initial geometry
        self.applyModeGeometry()

        # Keyboard hotkeys: 'S' toggles view mode, 'Esc' or 'Q' exits cleanly
        self.root.bind("<Key-s>", lambda event: self.toggleMode())
        self.root.bind("<Key-S>", lambda event: self.toggleMode())
        self.root.bind("<Escape>", lambda event: self.onCloseWindow())
        self.root.bind("<Key-q>", lambda event: self.onCloseWindow())
        self.root.bind("<Key-Q>", lambda event: self.onCloseWindow())

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

    def refreshHudLabels(self):
        """Update and format HUD label texts according to current mode width constraints."""
        maxChars = 110 if self.currentMode == "full" else 46

        # 1. Status with dynamic color
        color = "#00e676"  # green
        if "RECORDING" in self.statusText:
            color = "#ff1744"  # red
        elif "PROCESSING" in self.statusText or "ROUTING" in self.statusText:
            color = "#ffd600"  # yellow
        self.statusLabel.config(text=f"STATUS: {self.statusText}", fg=color)

        # 2. Transcript with mode-aware truncation
        displayTranscript = (
            self.transcriptText
            if len(self.transcriptText) <= maxChars
            else self.transcriptText[: maxChars - 3] + "..."
        )
        self.transcriptLabel.config(text=f"TRANSCRIPT: \"{displayTranscript}\"")

        # 3. Action with mode-aware truncation
        displayAction = (
            self.actionText
            if len(self.actionText) <= maxChars
            else self.actionText[: maxChars - 3] + "..."
        )
        self.actionLabel.config(text=f"ACTION: {displayAction}")

    def applyModeGeometry(self):
        """Update window geometry and position based on current mode."""
        if self.currentMode == "full":
            # Maximized window: full desktop view while keeping titlebar, close [X] and taskbar
            self.root.attributes("-fullscreen", False)
            self.root.state("zoomed")
            self.root.attributes("-topmost", True)
            if self.toggleButton:
                self.toggleButton.config(text="Split [S]")
        else:
            # Split PiP mode: docked safely in bottom-right corner above taskbar
            self.root.attributes("-fullscreen", False)
            self.root.state("normal")
            self.root.attributes("-topmost", True)

            pipWidth = 460
            pipHeight = 340

            workArea = getScreenWorkArea()
            if workArea:
                _, _, workRight, workBottom = workArea
                posX = workRight - pipWidth - 25
                posY = workBottom - pipHeight - 55
            else:
                posX = self.screenWidth - pipWidth - 25
                posY = self.screenHeight - pipHeight - 85

            posX = max(0, posX)
            posY = max(0, posY)

            self.root.geometry(f"{pipWidth}x{pipHeight}+{posX}+{posY}")
            if self.toggleButton:
                self.toggleButton.config(text="Full [S]")

        self.refreshHudLabels()

    def onCloseWindow(self):
        """Cleanly terminate camera hardware, UI, and harness process."""
        print("\n[CAMERA] Close request confirmed. Terminating Voice Action Harness cleanly...")
        self.cleanup()
        if self.root:
            try:
                self.root.destroy()
            except Exception:
                pass
        import os
        os._exit(0)

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
        hasHudUpdate = False
        while not self.hudQueue.empty():
            try:
                update = self.hudQueue.get_nowait()
                status = update.get("status")
                transcript = update.get("transcript")
                action = update.get("action")

                if status is not None:
                    self.statusText = status
                    hasHudUpdate = True

                if transcript is not None:
                    self.transcriptText = transcript
                    hasHudUpdate = True

                if action is not None:
                    self.actionText = action
                    hasHudUpdate = True

            except queue.Empty:
                break

        if hasHudUpdate:
            self.refreshHudLabels()

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
                    targetW = 460
                    targetH = 255

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
