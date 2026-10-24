import os
import subprocess
import webbrowser
import winsound

# Map common spoken application names to their Windows executable or URI
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
    "task manager": "taskmgr",
    "spotify": "spotify",
    "paint": "mspaint",
}


def openApplication(appName: str) -> str:
    """Launch a desktop application on Windows ONLY when the user explicitly commands to 'open', 'launch', or 'start' an app.
    Args:
        appName: Common name of the program to launch (e.g. chrome, notepad, calculator, vscode, terminal, explorer).
    """
    cleanName = appName.strip().lower()
    executable = appExecutableMap.get(cleanName, cleanName)

    try:
        subprocess.Popen(f"start {executable}", shell=True)
        winsound.MessageBeep(winsound.MB_OK)
        return f"[SUCCESS] Opened application: {appName}"
    except Exception as error:
        return f"[ERROR] Failed to open {appName}: {error}"


def closeApplication(appName: str) -> str:
    """Terminate an active desktop application ONLY when user explicitly commands to 'close', 'kill', or 'exit' an app.
    Args:
        appName: Name of the application to close (e.g. notepad, chrome, calc).
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
            return f"[WARNING] Could not close {appName} (process not found)."
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
    """Open a specific website URL ONLY when user explicitly commands to visit, browse to, or open a link/website.
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
    openApplication,
    closeApplication,
    searchWeb,
    openUrl,
]
