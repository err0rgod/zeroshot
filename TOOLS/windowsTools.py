import ctypes
import os
import subprocess
import threading
import time
import webbrowser
import winsound
from pathlib import Path

projectRoot = str(Path(__file__).resolve().parent.parent)

# Comprehensive map of desktop software and popular web applications
appExecutableMap = {
    # Windows Desktop Applications
    "chrome": "chrome",
    "google chrome": "chrome",
    "browser": "chrome",
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "terminal": "wt.exe",
    "windows terminal": "wt.exe",
    "powershell": "powershell.exe",
    "command prompt": "cmd.exe",
    "cmd": "cmd.exe",
    "code": "code",
    "vs code": "code",
    "vscode": "code",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "files": "explorer.exe",
    "task manager": "taskmgr.exe",
    "taskmanager": "taskmgr.exe",
    "taskmgr": "taskmgr.exe",
    "tasks": "taskmgr.exe",
    "spotify": "spotify",
    "paint": "mspaint.exe",

    # AI Developer Agents
    "claude": "claude",
    "claude code": "claude",
    "agy": "agy",
    "antigravity": "agy",

    # Popular Web Applications (Direct HTTPS destinations)
    "github": "https://www.github.com",
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "twitter": "https://www.x.com",
    "x": "https://www.x.com",
    "reddit": "https://www.reddit.com",
    "linkedin": "https://www.linkedin.com",
    "gmail": "https://mail.google.com",
}


def openApplication(targetName: str) -> str:
    """Open or launch any desktop application, software, or website on Windows (e.g. github, youtube, notepad, terminal, task manager, chrome, calc, twitter, claude, agy).
    Args:
        targetName: Name of the application or website to open (e.g. github, youtube, notepad, terminal, task manager).
    """
    cleanName = targetName.strip().lower()
    target = appExecutableMap.get(cleanName, cleanName)

    try:
        # 1. Web Applications & URLs
        if target.startswith("http://") or target.startswith("https://"):
            webbrowser.open(target)
            winsound.MessageBeep(winsound.MB_OK)
            return f"[SUCCESS] Opened website: {target}"

        if any(target.endswith(ext) for ext in [".com", ".org", ".net", ".io", ".dev", ".ai", ".in"]):
            url = target if target.startswith("http") else "https://" + target
            webbrowser.open(url)
            winsound.MessageBeep(winsound.MB_OK)
            return f"[SUCCESS] Opened URL: {url}"

        # 2. AI CLI Tools (launch in dedicated terminal window)
        if target in ["claude", "agy"]:
            cmdString = f'start cmd /k "cd /d {projectRoot} && {target}"'
            subprocess.Popen(cmdString, shell=True)
            winsound.MessageBeep(winsound.MB_OK)
            return f"[SUCCESS] Spawned {target.upper()} terminal session in workspace."

        # 3. Desktop Applications (ShellExecuteW handles UAC and desktop apps cleanly)
        res = ctypes.windll.shell32.ShellExecuteW(None, "open", target, None, None, 1)
        if res > 32:
            winsound.MessageBeep(winsound.MB_OK)
            return f"[SUCCESS] Opened application: {targetName}"

        # Fallback to shell start
        subprocess.Popen(f"start {target}", shell=True)
        winsound.MessageBeep(winsound.MB_OK)
        return f"[SUCCESS] Opened application: {targetName}"

    except Exception as error:
        return f"[ERROR] Failed to open {targetName}: {error}"


def closeApplication(targetName: str) -> str:
    """Close or terminate an active desktop application on Windows, or terminate the voice assistant.
    Args:
        targetName: Name of the application to close (e.g. notepad, chrome, calc, task manager, terminal), or 'exit' / 'assistant' to shut down.
    """
    cleanName = targetName.strip().lower()
    tokens = set(cleanName.replace("-", " ").replace("_", " ").split())

    # 1. System Shutdown Handlers (Exit / Quit / Stop / Shutdown)
    shutdownTokens = {"exit", "quit", "stop", "shutdown", "terminate", "assistant", "harness"}
    if cleanName in ["exit", "quit", "stop", "shutdown", "bye"] or bool(tokens & shutdownTokens):
        print("\n[SYSTEM] Exit command confirmed. Terminating Voice Action Harness cleanly...")
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
        # 400ms pause to flush audio chime and HUD before clean exit
        threading.Thread(target=lambda: (time.sleep(0.4), os._exit(0)), daemon=True).start()
        return "[SUCCESS] Shutting down Voice Action Harness cleanly."

    target = appExecutableMap.get(cleanName, cleanName)

    # Don't try to taskkill websites
    if target.startswith("http"):
        return f"[NOTICE] {targetName} is a website in your browser. Close the browser tab manually."

    if not target.endswith(".exe"):
        target += ".exe"

    try:
        result = subprocess.run(
            ["taskkill", "/f", "/im", target],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            return f"[SUCCESS] Closed application: {targetName}"
        else:
            reason = result.stderr.strip() or "Process not found."
            return f"[WARNING] Could not close {targetName} ({reason})."
    except Exception as error:
        return f"[ERROR] Failed to terminate {targetName}: {error}"


def searchWeb(query: str) -> str:
    """Search Google ONLY when the user explicitly commands to 'search for', 'google', or 'look up' something on the internet.
    Args:
        query: Specific search terms or query string.
    """
    try:
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        webbrowser.open(url)
        winsound.MessageBeep(winsound.MB_OK)
        return f"[SUCCESS] Searching web for: {query}"
    except Exception as error:
        return f"[ERROR] Failed to search web: {error}"


# Export list of registered tool functions for Cactus Needle 3
registeredTools = [
    openApplication,
    closeApplication,
    searchWeb,
]
