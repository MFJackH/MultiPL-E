"""
This Script takes a .json.gz file and extracts the prompt and completed source into a file that can be compiled.
"""

import argparse
import json
import gzip
import os

def get_args():
    args = argparse.ArgumentParser()
    args.add_argument(
        "--file",
        type=str,
        required=True,
        help="file to extract from. Must be a json.gz file"
    )
    args.add_argument(
        "--output-dir",
        type=str,
        required=False
    )
    return args.parse_args()

def main():
    args = get_args()
    filename = args.file
    with gzip.open(filename, 'r') as fin:
        data = json.loads(fin.read().decode('utf-8'))

    prompt = data["prompt"]
    completions = data["completions"]
    test = data["tests"]

    outfile_base = ""
    if args.output_dir:
        outfile_base = args.output_dir
    filename = os.path.basename(filename)
    first_ext_gone = os.path.splitext(filename)[0]
    filename = os.path.splitext(first_ext_gone)[0]
    print(filename)
    joined_path = os.path.join(outfile_base, filename)

    i = 0
    for completion in completions:
        outfile = joined_path + str(i) + ".cbl"
        with open(outfile, 'w') as of:
            of.write(prompt + completion + test)
        print(f"File: {outfile} written to disk")
        i +=1


if __name__ == "__main__":
    main()