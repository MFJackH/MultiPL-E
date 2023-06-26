# This script translates problems from the OpenAI HumanEval dataset into COBOL.
import re
import ast
from typing import List, Dict, Tuple

DOCSTRING_LINESTART_RE = re.compile("""\n(\s+)""")

class Translator:
    
    stop=["\ngoback."]

    ws=[]
    ws_count=0;

    prefix_last=True

    def __init__(self):
        self.int_type = "pic 9(4)"
        pass
    
    def cbl_preamble(self, name) -> str:
        return "\n".join([
                "identification division.",
                "program-id "+name,
                "working-storage section.",
        ])
    
    def gen_ws_name(self) -> str:
        name = f"test-{self.ws_count}"
        self.ws_count += 1
        return name
    
    def gen_ws(self, ann: ast.expr) -> str:
        if ann == None:
            raise Exception(f"No annotation")

        match ann:
            case ast.Name(id="int"):
               name = self.gen_ws_name()
               type = self.int_type
            case _other:
               raise Exception(f"Unhandled annotation: {ann}")
        
        self.ws.append(f"01 {name} {type}.")
        return name

    def translate_prompt(self, name: str, args: List[ast.arg], _returns, description: str) -> str:
        # Set up globals
        self.entry_point = name
        self.ret_ann = _returns
        # Do stuff
        cbl_description = "*>" + re.sub(DOCSTRING_LINESTART_RE, "\n*> ", description.strip()) + "\n"
        arg_list = ""
        for arg in args:
            arg_list = arg_list + arg.arg + " "
        return f"{self.cbl_preamble(name)}\nprocedure division using by value {arg_list}."
    
    def test_suite_prefix_lines(self, entry_point) -> List[str]:
        """
        Code for start of test suite.
        """
        return ["\ngoback.\n",
                f"{self.cbl_preamble('test_prog')}",
                "\n".join(self.ws),
                "procedure division."]
    
    def test_suite_suffix_lines(self) -> List[str]:
        """
        """
        return ["goback."]
    
    def deep_equality(self, left: str, right: str) -> str:
        """
        All tests are assertions that compare deep equality between left and right.
        """
        type=self.gen_ws(self.ret_ann)
        return "\n".join([
            f"{left}returning {type}.",
            f"if {type} = {right}",
            "    return true",
            "else",
            "    return false",
            "end-if"
        ])
    
    def finally_prepend(self) -> List[str]:
        return self.ws
    
    def gen_call(self, func: str, args: List[str]) -> str:
        """Translate a function call `func(args)`
        A function call f(x, y, z) translates to f(x, y, z)
        """
        arg_list = ""
        for arg in args:
            arg_list = arg_list + arg + " "

        if func == "candidate":
            func_name = self.entry_point
        else:
            func_name = func

        return f"call \"{func_name}\" using by value {arg_list}"
    
    # Below are todo. Produces typescript.

    def gen_literal(self, c: bool | str | int | float):
        """Translate a literal expression
        c: is the literal value
        """
        if type(c) == bool:
            return "true" if c else "false"
        elif type(c) == str:
            c = c.replace('\n','\\n')
            return f'"{c}"'
        elif c is None:
            return "undefined"
        return repr(c)

    def gen_var(self, v: str) -> str:
        """Translate a variable with name v."""
        return v

    def gen_list(self, l: List[str]) -> str:
        return "[" + ", ".join(l) + "]"

    def gen_tuple(self, t: List[str]) -> str:
        return "[" + ", ".join(t) + "]"

    def gen_dict(self, keys: List[str], values: List[str]) -> str:
        return "{" + ", ".join(f"{k}: {v}" for k, v in zip(keys, values)) + "}"
