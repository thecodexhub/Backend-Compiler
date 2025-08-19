import subprocess
import os
import tempfile
import uuid
import json
import shutil
from flask import Flask, request, jsonify

app = Flask(__name__)

DEFAULT_TIMEOUT = 6  # seconds; tweak as needed

def _ensure_cmd_exists(cmd):
    path = shutil.which(cmd)
    if not path:
        raise FileNotFoundError(f"Required command not found: {cmd}")
    return path

def _run(cmd, *, input_text="", cwd=None, timeout=DEFAULT_TIMEOUT):
    try:
        return subprocess.run(
            cmd,
            input=input_text,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
    except subprocess.TimeoutExpired as te:
        return subprocess.CompletedProcess(
            cmd,
            returncode=124,
            stdout=te.stdout or "",
            stderr=f"Timed out after {timeout}s"
        )

def compile_and_run(body):
    src_path = exe_path = None
    try:
        language = body.get("language")
        source_code = body.get("sourceCode")
        stdin_input = body.get("stdin", "")

        if not source_code or not language:
            return {"error": "Missing 'language' or 'sourceCode'"}

        file_id = str(uuid.uuid4())
        tmp_dir = tempfile.gettempdir()

        # ---------- C ----------
        if language == "c":
            _ensure_cmd_exists("gcc")
            src_path = os.path.join(tmp_dir, f"{file_id}.c")
            exe_path = os.path.join(tmp_dir, f"{file_id}")
            with open(src_path, "w") as f:
                f.write(source_code)

            compile_result = _run(["gcc", src_path, "-O2", "-static-libgcc", "-o", exe_path])
            if compile_result.returncode != 0:
                return {"compile_error": compile_result.stderr}

            run_result = _run([exe_path], input_text=stdin_input)

        # ---------- C++ ----------
        elif language == "cpp":
            _ensure_cmd_exists("g++")
            src_path = os.path.join(tmp_dir, f"{file_id}.cpp")
            exe_path = os.path.join(tmp_dir, f"{file_id}")
            with open(src_path, "w") as f:
                f.write(source_code)

            compile_result = _run(
                ["g++", src_path, "-O2", "-static-libgcc", "-static-libstdc++", "-o", exe_path]
            )
            if compile_result.returncode != 0:
                return {"compile_error": compile_result.stderr}

            run_result = _run([exe_path], input_text=stdin_input)

        # ---------- Java ----------
        elif language == "java":
            _ensure_cmd_exists("javac")
            _ensure_cmd_exists("java")
            src_path = os.path.join(tmp_dir, "Main.java")
            with open(src_path, "w") as f:
                f.write(source_code)

            compile_result = _run(["javac", "Main.java"], cwd=tmp_dir)
            if compile_result.returncode != 0:
                return {"compile_error": compile_result.stderr}

            run_result = _run(["java", "-cp", tmp_dir, "Main"], input_text=stdin_input)

        # ---------- Python ----------
        elif language == "python":
            src_path = os.path.join(tmp_dir, f"{file_id}.py")
            with open(src_path, "w") as f:
                f.write(source_code)
            run_result = _run(["python3", src_path], input_text=stdin_input)

        else:
            return {"error": f"Unsupported language: {language}"}

        return {
            "stdout": run_result.stdout,
            "stderr": run_result.stderr,
            "exitCode": run_result.returncode
        }

    except FileNotFoundError as e:
        return {"environment_error": str(e)}
    except Exception as e:
        return {"error": repr(e)}
    finally:
        try:
            if src_path and os.path.exists(src_path):
                os.remove(src_path)
            if exe_path and os.path.exists(exe_path):
                os.remove(exe_path)
            class_file = os.path.join(tempfile.gettempdir(), "Main.class")
            if os.path.exists(class_file):
                os.remove(class_file)
        except Exception:
            pass

# ------------------- Flask Endpoint -------------------
@app.route("/run", methods=["POST"])
def run_code():
    body = request.get_json(force=True)
    result = compile_and_run(body)
    return jsonify(result)

if __name__ == "__main__":
    # Render expects service to listen on port 10000
    app.run(host="0.0.0.0", port=10000)