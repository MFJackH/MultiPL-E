"""
This Script takes a directory filled with with .json.gz completions, and creates a fully formed program.
"""

import argparse
import json
import gzip
import os

def get_args():
    args = argparse.ArgumentParser()
    args.add_argument(
        "--completions-dir",
        type=str,
        required=True,
        help="Directory to extract from. Must contain json.gz files to turn into a program."
    )
    return args.parse_args()

def main():
    args = get_args()
    completions_dir = args.completions_dir
    for file in os.listdir(completions_dir):
        filename = os.path.join(completions_dir, file)
        with gzip.open(filename, 'r') as fin:
            data = json.loads(fin.read().decode('utf-8'))

        prompt = data["prompt"]
        completions = data["completions"]
        test = data["tests"]

        first_ext_gone = os.path.splitext(file)[0]
        base_name = os.path.splitext(first_ext_gone)[0]
        outfile_base = base_name + "-completions"
        outfile_base = os.path.join(completions_dir, outfile_base)
        os.mkdir(outfile_base)
        joined_path = os.path.join(outfile_base, base_name)

        i = 0
        for completion in completions:
            outfile = joined_path + str(i) + ".cbl"
            with open(outfile, 'w') as of:
                try:
                    of.write(prompt + completion + test)
                except:
                    continue
            print(f"File: {outfile} written to disk")
            i +=1


if __name__ == "__main__":
    main()