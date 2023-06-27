import os
from pathlib import Path
from safe_subprocess import run

LANG_NAME = "COBOL"
LANG_EXT = ".sh"

def eval_script(path: Path):
    my_env = os.environ.copy()
    my_env["PATH"] = f"/opt/microfocus/EnterpriseDeveloper/bin{my_env['PATH']}"
    my_env["COBCPY"] = f"/opt/microfocus/EnterpriseDeveloper/cpylib"
    my_env["COBDIR"] = f"/opt/microfocus/EnterpriseDeveloper"
    my_env["CLASSPATH"] = f".:/opt/microfocus/EnterpriseDeveloper/lib/mfcobolrts.jar:/opt/microfocus/EnterpriseDeveloper/lib/mfcobol.jar:/opt/microfocus/EnterpriseDeveloper/lib/mfsqljvm.jar:/opt/microfocus/EnterpriseDeveloper/lib/mfidmr.jar"
    my_env["LD_LIBRARY_PATH"] = f"/opt/microfocus/EnterpriseDeveloper/lib"

    build_result = run(["cob", "-x", path, "-o", "testit.exe"], env=my_env)
    if build_result.exit_code != 0:
        return {
            "status": "SyntaxError",
            "exit_code": build_result.exit_code,
            "stdout": build_result.stdout,
            "stderr": build_result.stderr,
        }
    
    run_result = run(["./testit.exe"])

    if run_result.timeout:
        status = "Timeout"
    elif "fail" in run_result.stdout:
        status = "Exception"
    else:
        status = "OK"

    return {
        "status": status,
        "exit_code": run_result.exit_code,
        "stdout": run_result.stdout,
        "stderr": run_result.stderr,
    }