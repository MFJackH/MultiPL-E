"""
This Script takes a .json.gz file and extracts the prompt and completed source into a file that can be compiled.
"""

import argparse
import json
import gzip

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

    outfile_base = ""
    if args.output_dir:
        outfile_base = args.output_dir
    outfile_base += (filename.split('\\')[-1]).split('.')[0]

    #Write out the test program
    testfile_name = outfile_base + "_test.cbl"
    with open(testfile_name, "w") as oft:
        oft.write(data["tests"])

    #Write out the programs generated from the LLM
    i = 0
    for completion in completions:
        outfile = outfile_base + str(i) + ".cbl"
        with open(outfile, 'w') as of:
            of.write(prompt + completion)
        print(f"File: {outfile} written to disk")
        i +=1


if __name__ == "__main__":
    main()