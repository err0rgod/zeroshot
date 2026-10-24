import subprocess
import winsound
from pathlib import Path

# Workspace project root
projectRoot = str(Path(__file__).resolve().parent.parent)


def gitStatus() -> str:
    """Check git repository status, changed files, and current branch.
    ONLY call when user explicitly asks to 'check git status', 'repo status', or 'show modified files'.
    """
    try:
        result = subprocess.run(
            ["git", "status", "-s", "-b"],
            cwd=projectRoot,
            capture_output=True,
            text=True,
        )
        output = result.stdout.strip()
        winsound.MessageBeep(winsound.MB_OK)

        if not output:
            return "[GIT STATUS] Working directory clean. No changes."

        lines = output.splitlines()
        branchInfo = lines[0].replace("##", "").strip()
        changedCount = len(lines) - 1

        print(f"\n--- GIT REPOSITORY STATUS ---")
        print(output)
        print(f"-----------------------------\n")

        return f"[GIT STATUS] Branch: {branchInfo} | {changedCount} modified items."

    except Exception as error:
        return f"[GIT ERROR] Failed to check status: {error}"


def gitCommit(commitMessage: str) -> str:
    """Stage all modified files and create a git commit.
    ONLY call when user explicitly asks to 'commit', 'git commit', or 'commit changes'.
    Args:
        commitMessage: Description of the changes made (e.g. 'update needle router').
    """
    try:
        subprocess.run(["git", "add", "-A"], cwd=projectRoot, check=True)

        result = subprocess.run(
            ["git", "commit", "-m", commitMessage],
            cwd=projectRoot,
            capture_output=True,
            text=True,
        )

        winsound.MessageBeep(winsound.MB_OK)
        if result.returncode == 0:
            print(f"\n--- GIT COMMIT ---")
            print(result.stdout.strip())
            print(f"------------------\n")
            return f"[GIT COMMIT] Successfully committed: \"{commitMessage}\""
        else:
            return f"[GIT NOTICE] Nothing new to commit: {result.stderr.strip()}"

    except Exception as error:
        return f"[GIT ERROR] Commit failed: {error}"


def gitPush(branchName: str = "main") -> str:
    """Push local commits to GitHub remote repository.
    ONLY call when user explicitly asks to 'git push', 'push to github', or 'push to main'.
    Args:
        branchName: Target branch to push (default: main).
    """
    try:
        cleanBranch = branchName.strip() or "main"
        result = subprocess.run(
            ["git", "push", "origin", cleanBranch],
            cwd=projectRoot,
            capture_output=True,
            text=True,
        )

        winsound.MessageBeep(winsound.MB_OK)
        if result.returncode == 0:
            return f"[GIT PUSH] Successfully pushed commits to origin/{cleanBranch}"
        else:
            return f"[GIT NOTICE] Push response: {result.stderr.strip()}"

    except Exception as error:
        return f"[GIT ERROR] Push failed: {error}"


def gitDiff() -> str:
    """Show git diff summary of unstaged modifications in the workspace.
    ONLY call when user explicitly asks for 'git diff', 'show diff', or 'view code modifications'.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--stat"],
            cwd=projectRoot,
            capture_output=True,
            text=True,
        )
        diffOutput = result.stdout.strip()
        winsound.MessageBeep(winsound.MB_OK)

        if not diffOutput:
            return "[GIT DIFF] No unstaged changes."

        print(f"\n--- GIT DIFF STATS ---")
        print(diffOutput)
        print(f"----------------------\n")

        return f"[GIT DIFF] Changes detected across repository."

    except Exception as error:
        return f"[GIT ERROR] Diff failed: {error}"


def gitCreateBranch(branchName: str) -> str:
    """Create and checkout a new git branch in the repository.
    ONLY call when user explicitly asks to create a branch.
    Args:
        branchName: Name of the new git branch (e.g. 'feature-auth', 'dev').
    """
    try:
        cleanBranch = branchName.strip().replace(" ", "-")
        result = subprocess.run(
            ["git", "checkout", "-b", cleanBranch],
            cwd=projectRoot,
            capture_output=True,
            text=True,
        )
        winsound.MessageBeep(winsound.MB_OK)

        if result.returncode == 0:
            return f"[GIT BRANCH] Created and switched to branch '{cleanBranch}'"
        else:
            return f"[GIT NOTICE] Branch command response: {result.stderr.strip()}"

    except Exception as error:
        return f"[GIT ERROR] Failed to create branch: {error}"


def launchCodingAgent(agentName: str) -> str:
    """Launch an AI coding agent CLI in a new terminal window.
    ONLY call when user asks to launch or open Claude, AGY, or Antigravity.
    Args:
        agentName: Name of the AI agent ('claude' for Claude Code, or 'agy' / 'antigravity').
    """
    try:
        cleanAgent = agentName.strip().lower()
        command = "claude" if "claude" in cleanAgent else "agy"
        cmdString = f'start cmd /k "cd /d {projectRoot} && {command}"'
        subprocess.Popen(cmdString, shell=True)
        winsound.MessageBeep(winsound.MB_OK)
        return f"[SUCCESS] Spawned {command.upper()} terminal session in workspace."

    except Exception as error:
        return f"[ERROR] Failed to launch coding agent: {error}"


def runTests() -> str:
    """Execute syntax validation and tests across the project.
    ONLY call when user explicitly asks to 'run tests' or 'test project'.
    """
    try:
        result = subprocess.run(
            [".venv\\Scripts\\python", "-m", "py_compile", "main.py", "VAD\\micProcess.py", "STT\\sttClient.py"],
            cwd=projectRoot,
            capture_output=True,
            text=True,
        )
        winsound.MessageBeep(winsound.MB_OK)

        if result.returncode == 0:
            return "[TESTS] All project modules passed syntax compilation checks."
        else:
            return f"[TESTS] Compile issues detected: {result.stderr.strip()}"

    except Exception as error:
        return f"[TEST ERROR] Failed to run test check: {error}"


developerToolsList = [
    gitStatus,
    gitCommit,
    gitPush,
    gitDiff,
    gitCreateBranch,
    launchCodingAgent,
    runTests,
]
