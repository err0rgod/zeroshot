import sys
import time
from pathlib import Path
from needle import Needle

# Ensure project root is in sys.path
projectRoot = Path(__file__).resolve().parent.parent
if str(projectRoot) not in sys.path:
    sys.path.append(str(projectRoot))

from TOOLS import allRegisteredTools
from TOOLS.windowsTools import appExecutableMap

# Map tool names to their callable functions
toolMap = {fn.__name__: fn for fn in allRegisteredTools}

# Cached singleton instance for lazy initialization
needleModel = None


def getNeedleModel():
    """Lazily load Needle 3 model weights only when tool routing is actually needed."""
    global needleModel
    if needleModel is None:
        print("[NEEDLE] Pre-loading Edge Tool Router (Generation 3)...")
        needleModel = Needle(tools=allRegisteredTools, generation=3, stateless=True)
        print(f"[NEEDLE] Router ready with {len(allRegisteredTools)} registered developer & OS tools.\n")
    return needleModel


def routeAndExecute(promptText: str, minConfidence: float = 0.25) -> dict:
    """
    Route natural language command through Needle 3.
    Uses Needle's confidence head and intent guards to automatically ignore
    casual chatter, video intros, or irrelevant speech (confidence < 0.25).
    """
    if not promptText or not promptText.strip():
        return {}

    cleanPrompt = promptText.strip().lower()

    # Instant exit command check (no model latency, 0ms termination)
    exitPhrases = {
        "exit", "quit", "stop", "shutdown", "terminate", "bye", "goodbye",
        "exit assistant", "close assistant", "stop assistant", "quit assistant", "shutdown assistant",
        "exit program", "close program", "stop program", "quit program",
        "exit the app", "close the app", "quit the app",
        "exit now", "quit now"
    }
    if cleanPrompt in exitPhrases or cleanPrompt.startswith("exit ") or cleanPrompt.startswith("quit "):
        promptWords = cleanPrompt.split()
        secondWord = promptWords[1] if len(promptWords) > 1 else ""
        if secondWord and secondWord in appExecutableMap:
            print(f"\n[ROUTER] Routing close command for application: {secondWord}")
            return {"results": [toolMap["closeApplication"](targetName=secondWord)]}

        print("\n[ROUTER] Exit command recognized directly.")
        toolMap["closeApplication"](targetName="exit")
        return {"results": ["[SUCCESS] Shutting down Voice Action Harness cleanly."]}

    startTime = time.perf_counter()
    try:
        # Step 1: Infer intent and tool calls without running them
        model = getNeedleModel()
        response = model.complete(promptText.strip())
        latencyMs = int((time.perf_counter() - startTime) * 1000)

        confidence = response.get("confidence", 0.0)
        functionCalls = response.get("function_calls") or response.get("suppressed_calls", [])

        # Step 2: Guardrail check. If confidence is low or no tool matches, ignore it!
        if confidence < minConfidence or not functionCalls:
            print(f"[ROUTER ({latencyMs}ms)]: Ignored (Casual speech / confidence: {confidence:.2f})")
            return response

        # Step 3: Tool-specific sanity check to avoid accidental trigger on casual words
        results = []

        for call in functionCalls:
            toolName = call.get("name")
            arguments = call.get("arguments", {})

            # Semantic guard for zero-argument tools to prevent false positives during intros
            if toolName == "gitDiff" and not any(w in cleanPrompt for w in ["diff", "changes", "modified"]):
                print(f"[ROUTER ({latencyMs}ms)]: Ignored false match for gitDiff (confidence: {confidence:.2f})")
                continue

            # Semantic guard for git push (must contain 'push')
            if toolName == "gitPush" and "push" not in cleanPrompt:
                if any(w in cleanPrompt for w in ["open", "launch", "goto", "visit"]):
                    toolName = "openApplication"
                    arguments = {"targetName": "github"}
                else:
                    print(f"[ROUTER ({latencyMs}ms)]: Ignored false match for gitPush without 'push' keyword")
                    continue

            targetTool = toolMap.get(toolName)
            if targetTool:
                actionResult = targetTool(**arguments)
                results.append(actionResult)
                print(f"[ACTION ({latencyMs}ms)]: {actionResult} (confidence: {confidence:.2f})")
            else:
                print(f"[WARNING] Unrecognized tool name: {toolName}")

        response["results"] = results
        return response

    except Exception as error:
        print(f"[ERROR] [Router Exception]: {error}")
        return {"error": str(error)}


if __name__ == "__main__":
    # Test 1: Casual conversation (Should be ignored)
    casualSpeech = "Hey guys welcome to my portfolio video today I built an AI agent"
    print(f"Testing casual speech: \"{casualSpeech}\"")
    routeAndExecute(casualSpeech)

    print("-" * 50)

    # Test 2: Developer command (Should execute)
    devCommand = "Check git status"
    print(f"Testing developer command: \"{devCommand}\"")
    routeAndExecute(devCommand)
