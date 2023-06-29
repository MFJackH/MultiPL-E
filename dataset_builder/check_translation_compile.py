import argparse
from generic_translator import list_originals, translate_prompt_and_tests
import os
import subprocess
import sys

TESTERS = {
    "cpp": { "translator": "humaneval_to_cpp", "build": {"win": "cl", "lin": "g++"}, "extension": "cpp" },
    "cbl": { "translator": "humaneval_to_cbl", "build": {"win": "cbllink", "lin": "cob"}, "extension": "cbl" }
}
test_translation_path = "translated_prompts_and_tests"

def main():
    args = argparse.ArgumentParser()
    args.add_argument(
        "--lang", type=str, help="Language to translate to"
    )
    args.add_argument(
        "--doctests",
        type=str,
        default="transform",
        help="What to do with doctests: keep, remove, or transform",
    )
    args.add_argument(
        "--prompt-terminology",
        type=str,
        default="reworded",
        help="How to translate terminology in prompts: verbatim or reworded"
    )
    args.add_argument(
        "--originals",
        type=str,
        help="Originals to use for translation",
        default="../datasets/originals"
    )
    parsed_args = args.parse_args()

    # Delete exist test translations
    if os.path.exists(test_translation_path):
        for file in os.listdir(test_translation_path):
            joined_file = os.path.join(test_translation_path, file)
            os.remove(joined_file)
        os.rmdir(test_translation_path)

    os.makedirs(test_translation_path)

    if sys.platform.startswith('win'):
        platform = "win"
    elif sys.platform.startswith('linux'):
        platform = "lin"
    else:
        raise Exception("Invalid platform")

    translator_use = __import__(TESTERS[parsed_args.lang]["translator"]).Translator()

    # Loop through all problems in chosen set
    originals = list_originals(parsed_args.originals)
    compiler_fails = 0
    skip_fails = 0
    for original in originals.values():
        result = translate_prompt_and_tests(original, translator_use, parsed_args.doctests, parsed_args.prompt_terminology)

        if result is None:
            print(f"Translation fail for: {original}")
            skip_fails+= 1
            continue

        (prompt, tests) = result

        # Create compilable file of correct form
        file_name = os.path.basename(original)
        file_name_no_extension = os.path.splitext(file_name)[0]
        extension = "." + TESTERS[parsed_args.lang]["extension"]
        file_path = os.path.join(test_translation_path, file_name_no_extension)
        file_path_extension = file_path + extension

        with open(file_path_extension, "w") as file:
            print(f"Writing prompt translation to {file_path_extension}")
            content = prompt + tests
            file.write(content)
        
        # Add compilation process here
        if(parsed_args.lang == "cbl"):
            if(platform == "win"):
                with open("directives.dir", "w") as file:
                    file.write("SOURCEFORMAT(FREE)")
                result = subprocess.run([TESTERS[parsed_args.lang]["build"][platform], f"-O{test_translation_path}\{file_name_no_extension}.exe", "-Udirectives.dir", file_path_extension], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                result = subprocess.run([TESTERS[parsed_args.lang]["build"][platform], "-x", file_path_extension], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif(parsed_args.lang == "cpp"):
            if(platform == "win"):
                result = subprocess.run([TESTERS[parsed_args.lang]["build"][platform], file_path_extension], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                result = None
            else:
                result = subprocess.run([TESTERS[parsed_args.lang]["build"][platform], "-o", file_path_extension, "-std=c++17"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            raise Exception("No implementation for this language")

        if (result.returncode):
            compiler_fails += 1

    print(f"Translation fails {skip_fails} / {len(originals)}")
    print(f"Compiler fails {compiler_fails} / {len(originals)}")

if __name__ == "__main__":
    main()
