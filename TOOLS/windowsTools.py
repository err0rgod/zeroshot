import ctypes
import os
import subprocess
import webbrowser
import winsound
from pathlib import Path

projectRoot = str(Path(__file__).resolve().parent.parent)

# Map common spoken application names to executable or target command
appExecutableMap = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "browser": "chrome",
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "terminal": "wt",
    "powershell": "powershell",
    "command prompt": "cmd",
    "cmd": "cmd",
    "code": "code",
    "vs code": "code",
    "vscode": "code",
    "explorer": "explorer",
    "file explorer": "explorer",
    "files": "explorer",
    "task manager": "taskmgr.exe",
    "taskmanager": "taskmgr.exe",
    "taskmgr": "taskmgr.exe",
    "tasks": "taskmgr.exe",
    "spotify": "spotify",
    "paint": "mspaint",
    "claude": "claude",
    "claude code": "claude",
    "agy": "agy",
    "antigravity": "agy",
}


def launchApplication(appName: str) -> str:
    """Launch or open desktop applications and developer tools on Windows (e.g. task manager, chrome, notepad, calculator, claude, agy, terminal, explorer).
    Args:
        appName: Common name of the application to launch (e.g. task manager, chrome, notepad, calc, claude, agy).
    """
    cleanName = appName.strip().lower()
    target = appExecutableMap.get(cleanName, cleanName)

    try:
        # 1. AI CLI tools need an interactive terminal session
        if target in ["claude", "agy"]:
            cmdString = f'start cmd /k "cd /d {projectRoot} && {target}"'
            subprocess.Popen(cmdString, shell=True)
            winsound.MessageBeep(winsound.MB_OK)
            return f"[SUCCESS] Spawned {target.upper()} terminal session in workspace."

        # 2. Windows System apps (like Task Manager): use ShellExecuteW to bypass UAC redirection
        res = ctypes.windll.shell32.ShellExecuteW(None, "open", target, None, None, 1)
        if res > 32:
            winsound.MessageBeep(winsound.MB_OK)
            return f"[SUCCESS] Opened application: {appName}"

        # 3. Fallback to shell start
        subprocess.Popen(f"start {target}", shell=True)
        winsound.MessageBeep(winsound.MB_OK)
        return f"[SUCCESS] Opened application: {appName}"

    except Exception as error:
        return f"[ERROR] Failed to open {appName}: {error}"


def closeApplication(appName: str) -> str:
    """Close or terminate an active desktop application on Windows.
    Args:
        appName: Name of the application to close (e.g. notepad, chrome, calc, task manager).
    """
    cleanName = appName.strip().lower()
    targetName = appExecutableMap.get(cleanName, cleanName)
    if not targetName.endswith(".exe"):
        targetName += ".exe"

    try:
        result = subprocess.run(
            ["taskkill", "/f", "/im", targetName],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            return f"[SUCCESS] Closed application: {appName}"
        else:
            reason = result.stderr.strip() or "Process not found."
            return f"[WARNING] Could not close {appName} ({reason})."
    except Exception as error:
        return f"[ERROR] Failed to terminate {appName}: {error}"


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


def openUrl(url: str) -> str:
    """Open a website URL in the browser ONLY when the prompt includes a web address or domain (e.g. .com, .org, youtube, github, twitter). Never call for desktop applications.
    Args:
        url: Full web address or domain (e.g. https://github.com, youtube.com).
    """
    try:
        cleanUrl = url.strip()
        if not cleanUrl.startswith("http://") and not cleanUrl.startswith("https://"):
            cleanUrl = "https://" + cleanUrl
        webbrowser.open(cleanUrl)
        winsound.MessageBeep(winsound.MB_OK)
        return f"[SUCCESS] Opened URL: {cleanUrl}"
    except Exception as error:
        return f"[ERROR] Failed to open URL: {error}"


# Export list of registered tool functions for Cactus Needle 3
registeredTools = [
    launchApplication,
    closeApplication,
    searchWeb,
    openUrl,
]
