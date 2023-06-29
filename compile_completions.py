import subprocess
import argparse
import os

args = argparse.ArgumentParser()
args.add_argument(
    "--completions", type=str, help="Directory containing folders, each with .cbl completions to compile"
)
parsed_args = args.parse_args()

successes = 0
success_list = []
for root, dirs, files in os.walk(parsed_args.completions):
    for file in files:
        file_path = os.path.join(root, file)
        _, file_extension = os.path.splitext(file_path)

        if file_extension == ".cbl":
            print(f"Compiling: {file_path}")
            result = subprocess.run(["cobol", file_path, "SOURCEFORMAT(FREE)", ";"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if result.returncode == 0:
                successes += 1
                success_list.append(file_path)
            print(f"Success count: {successes}")

print(f"COBOL prompts, completion and test programs compiled: {successes}")
print(success_list)