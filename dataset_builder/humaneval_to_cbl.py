# This script translates problems from the OpenAI HumanEval dataset into COBOL.
import re
import ast
from typing import List, Dict, Tuple

DOCSTRING_LINESTART_RE = re.compile("""\n(\s+)""")

class Translator:
    
    cols="        "
    
    stop=["\ngoback."]

    ws=[]
    ws_count=0;
    structure_initialisation=[]

    prefix_last=True

    def __init__(self):
        self.bool_type = "pic x comp-x"
        self.int_type = "pic s9(9)"
        self.float_type = "pic s9(9)"
        self.str_type = "pic x(n)"
        self.list_type = "pic x(elem_size) occurs n"
        pass
    
    def indent_all(self, list) -> List[str]:
        return [f"{self.cols}{i}" for i in list]

    def list_to_indent_str(self, list) -> str:
        return "\n".join(self.indent_all(list))
    
    def cbl_preamble(self, name) -> str:
        preamble = [
            "identification division.",
            "program-id "+name+".",
            "working-storage section.",
        ]
        return preamble 
    
    def gen_ws_name(self, ann) -> str:
        match ann:
            case ast.Name(id="bool"):
                name = f"bool-{self.ws_count}"
            case ast.Name(id="int"):
                name = f"int-{self.ws_count}"
            case ast.Name(id="float"):
                name = f"float-{self.ws_count}"
            case ast.Name(id="str"):
                name = f"str-{self.ws_count}"
            case ast.List():
                name = f"list-{self.ws_count}"

        self.ws_count += 1
        return name
    
    def gen_ws(self, ann: ast.expr) -> str:
        if ann == None:
            raise Exception(f"No annotation")

        name = self.gen_ws_name(ann)

        match ann:
            case ast.Name(id="bool"):
                type = self.bool_type
            case ast.Name(id="int"):
                type = self.int_type
            case ast.Name(id="float"):
                type = self.float_type
            case ast.Name(id="str"):
                type = self.str_type
            case ast.List():
                type = self.list_type
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

        prompt = self.cbl_preamble(name)
        prompt.append(f"procedure division using by value {arg_list[:-1]}.")
        return self.list_to_indent_str(prompt)
    
    def test_suite_prefix_lines(self, entry_point) -> List[str]:
        """
        Code for start of test suite. Actually added at the end... :)
        """
        prefix = ["", "goback.", ""]
        prefix = prefix + self.cbl_preamble('test_prog')
        prefix = prefix + self.ws
        prefix = prefix + ["procedure division."]
        prefix = prefix + self.structure_initialisation
        return self.indent_all(prefix)
    
    def test_suite_suffix_lines(self) -> List[str]:
        """
        """
        return self.indent_all(["goback."])
    
    def deep_equality(self, left: Tuple[str, ast.Expr], right: Tuple[str, ast.Expr]) -> str:
        """
        All tests are assertions that compare deep equality between left and right.
        """

        lvalue, _ = left
        rvalue, _ = right

        type=self.gen_ws(self.ret_ann)
        equality = [
            f"{lvalue}returning {rvalue}.",
            f"if {type} = {rvalue}",
            "    return true",
            "else",
            "    return false",
            "end-if"]
        return self.list_to_indent_str(equality)
    
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

        return self.list_to_indent_str([f"call \"{func_name}\" using by value {arg_list}"])
    
    # Below are todo. Produces typescript.

    def gen_literal(self, c: bool | str | int | float) -> Tuple[str, ast.Name]:
        """Translate a literal expression
        c: is the literal value
        """
        if type(c) == bool:
            return "true" if c else "false", ast.Name("bool")
        elif type(c) == str:
            c = c.replace('\n','\\n'), ast.Name("str")
            return f'"{c}"'
        elif type(c) == int:
            return repr(c), ast.Name("int")
        elif type(c) == float:
            return repr(c), ast.Name("float")
        elif type(c) is None:
            return "undefined", ast.Name("None")
        else:
            return repr(c) 

    def gen_var(self, v: str) -> str:
        """Translate a variable with name v."""
        return v

    def gen_list(self, l: List[Tuple[str, ast.Expr]]) -> str:
        list_element_type = ast.List()
        name = self.gen_ws(list_element_type)

        # List Initialisation
        if len(l) != 0:
            self.structure_initialisation.append(f"*> Initialisation for {name}")
            for position, (elem, _) in enumerate(l):
                self.structure_initialisation.append(f"move {elem} to {name}({position})")

        return name, ast.List()

    def gen_list_type(self, l: List[Tuple[str, ast.Expr]]) -> str:
        elem_type = l[0][1]
        if elem_type.id in self.literal_types.keys():
            return f"pic {self.literal_types[elem_type.id]} occurs {len(l)}"


    def gen_tuple(self, t: List[str]) -> str:
        return "[" + ", ".join(t) + "]"

    def gen_dict(self, keys: List[str], values: List[str]) -> str:
        return "{" + ", ".join(f"{k}: {v}" for k, v in zip(keys, values)) + "}"

    def gen_call(self, func: str, args: List[str]) -> str:
        """Translate a function call `func(args)`
        A function call f(x, y, z) translates to f(x, y, z)
        """
        arg_list = ""
        for value, type in args:
            arg_list += value + " "

        if func == "candidate":
            func_name = self.entry_point
        else:
            func_name = func

        return f"call \"{func_name}\" using by value {arg_list}", ast.Call()