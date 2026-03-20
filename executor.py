# backend/executor.py
#
# Runs generated code in a secure E2B cloud sandbox.
# The sandbox is completely isolated — malicious code cannot
# affect your server or the user's machine.

import os
import logging
from e2b_code_interpreter import Sandbox

logger = logging.getLogger(__name__)


def run_code_in_sandbox(files: dict[str, str], project_type: str) -> dict:
    """
    Takes all generated files, runs the main entry point in a sandbox,
    and returns the results in a format the frontend can display.

    files = { "main.py": "print('hello')", "utils.py": "..." }
    project_type = "python" | "web" | "javascript"

    Returns:
    {
        "success": True/False,
        "output": "stdout text",
        "error": "stderr text or None",
        "test_results": "test output or None",
        "summary": "plain English explanation of what happened"
    }
    """
    try:
        with Sandbox(api_key=os.getenv("E2B_API_KEY"), timeout=60) as sandbox:

            # Write all generated files into the sandbox filesystem
            for file_path, content in files.items():
                sandbox.files.write(f"/home/user/{file_path}", content)

            results = {
                "success": False,
                "output": "",
                "error": None,
                "test_results": None,
                "summary": ""
            }

            if project_type == "python":
                # Install dependencies if requirements.txt exists
                if "requirements.txt" in files:
                    install = sandbox.run_code(
                        "import subprocess; "
                        "r = subprocess.run(['pip', 'install', '-r', "
                        "'/home/user/requirements.txt', '-q'], "
                        "capture_output=True, text=True); "
                        "print(r.stdout); print(r.stderr)"
                    )

                # Run main entry point
                main_file = _find_main_file(files, "python")
                if main_file:
                    execution = sandbox.run_code(
                        f"import subprocess; r = subprocess.run("
                        f"['python', '/home/user/{main_file}'], "
                        f"capture_output=True, text=True, timeout=30); "
                        f"print('STDOUT:', r.stdout); "
                        f"print('STDERR:', r.stderr); "
                        f"print('EXIT_CODE:', r.returncode)"
                    )
                    output = execution.text or ""
                    results["output"] = output
                    results["success"] = "EXIT_CODE: 0" in output
                    if "EXIT_CODE: 0" not in output:
                        results["error"] = _extract_stderr(output)

                # Run tests if test files exist
                test_files = [f for f in files if f.startswith("test_") or f.endswith("_test.py")]
                if test_files:
                    test_exec = sandbox.run_code(
                        "import subprocess; r = subprocess.run("
                        "['python', '-m', 'pytest', '/home/user/', '-v', '--tb=short'], "
                        "capture_output=True, text=True, cwd='/home/user'); "
                        "print(r.stdout)"
                    )
                    results["test_results"] = test_exec.text

            elif project_type in ("web", "javascript"):
                # Install npm dependencies
                if "package.json" in files:
                    sandbox.run_code(
                        "import subprocess; subprocess.run("
                        "['npm', 'install'], cwd='/home/user', "
                        "capture_output=True)"
                    )

                # Run with node
                main_file = _find_main_file(files, "javascript")
                if main_file:
                    execution = sandbox.run_code(
                        f"import subprocess; r = subprocess.run("
                        f"['node', '/home/user/{main_file}'], "
                        f"capture_output=True, text=True, timeout=15); "
                        f"print(r.stdout); print(r.stderr)"
                    )
                    results["output"] = execution.text or ""
                    results["success"] = not ("Error" in (execution.text or ""))

            # Build a plain-English summary
            results["summary"] = _build_summary(results, project_type, files)
            return results

    except Exception as e:
        logger.error(f"Sandbox execution failed: {e}")
        return {
            "success": False,
            "output": "",
            "error": str(e),
            "test_results": None,
            "summary": f"Could not run the code: {str(e)}"
        }


def _find_main_file(files: dict, project_type: str) -> str | None:
    """Find the most likely entry point file."""
    # Priority order for Python
    python_candidates = ["main.py", "app.py", "run.py", "server.py", "index.py"]
    js_candidates = ["index.js", "main.js", "app.js", "server.js"]

    candidates = python_candidates if project_type == "python" else js_candidates
    for candidate in candidates:
        if candidate in files:
            return candidate

    # Fall back to first file of right type
    ext = ".py" if project_type == "python" else ".js"
    for filename in files:
        if filename.endswith(ext) and not filename.startswith("test"):
            return filename
    return None


def _extract_stderr(output: str) -> str:
    """Pull out just the error lines."""
    lines = output.split("\n")
    error_lines = [l for l in lines if "Error" in l or "Traceback" in l or "STDERR:" in l]
    return "\n".join(error_lines) if error_lines else output


def _build_summary(results: dict, project_type: str, files: dict) -> str:
    """
    Build a plain-English summary a non-technical person can understand.
    This is what gets shown prominently in the UI.
    """
    file_count = len(files)
    file_list = ", ".join(list(files.keys())[:5])

    if results["success"]:
        base = f"✅ The code ran successfully without any errors. "
        base += f"{file_count} files were generated ({file_list}"
        base += " and more" if file_count > 5 else ""
        base += "). "

        if results["test_results"]:
            # Count passed tests
            passed = results["test_results"].count(" PASSED")
            failed = results["test_results"].count(" FAILED")
            if failed == 0:
                base += f"All {passed} automated tests passed. "
            else:
                base += f"{passed} tests passed, {failed} failed. "

        if results["output"] and len(results["output"].strip()) > 0:
            # Show first line of output
            first_line = results["output"].strip().split("\n")[0]
            if len(first_line) < 100:
                base += f"Program output: \"{first_line}\""
        return base
    else:
        base = f"⚠️ The code was generated but encountered an issue when running. "
        if results["error"]:
            base += f"The error was: {results['error'][:150]}"
        base += ". The code may still be correct for its purpose — "
        base += "some programs require specific setup or data to run."
        return base