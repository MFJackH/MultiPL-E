# This script translates problems from the OpenAI HumanEval dataset into COBOL.
import re
import ast
from typing import List, Dict, Tuple

DOCSTRING_LINESTART_RE = re.compile("""\n(\s+)""")

class Translator:
    
    cols="       "
    
    stop=["\ngoback."]


    prefix_last=True

    def __init__(self):
        self.ws = []
        self.ws_count=0;
        self.structure_initialisation=[]
        self.sections = []
        self.literal_types = {
            "bool": "pic x comp-x",
            "int": "pic x(4) comp-x",
            "float": "pic 9(9)v99",
            "str": "pic x(256)"
        }
    
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
    
    def gen_data_item(self, ann: ast.expr, list) -> str:
        if ann == None:
            raise Exception(f"No annotation")

        match ann:
            case ast.Name(id=_):
                ws_type = self.literal_types[ann.id]
                name = f"{ann.id}-{self.ws_count}"
            case ast.List():
                ws_type = self.gen_list_type(ann.elts)
                name = f"list-{self.ws_count}"
            case _:
                raise Exception(f"Unhandled annotation: {ann}")

        self.ws_count += 1
        list.append(f"01 {name} {ws_type}.")
        return name

    def translate_prompt(self, name: str, args: List[ast.arg], _returns, description: str) -> str:
        # Set up globals
        self.entry_point = name
        self.ret_ann = _returns
        # Do stuff
        cbl_description = "*>" + re.sub(DOCSTRING_LINESTART_RE, "\n*> ", description.strip()) + "\n"
        arg_list = ""
        linkage = []
        for arg in args:
            arg_list = arg_list + arg.arg + " "
            # self.gen_data_item(arg.annotation, linkage)

        prompt = self.cbl_preamble(name)
        prompt += ["linkage section."] 
        # Parameters
        prompt += linkage
        prompt.append(f"procedure division using by value {arg_list[:-1]}.")
        return self.list_to_indent_str(prompt)
    
    def test_suite_prefix_lines(self, entry_point) -> List[str]:
        """
        Code for start of test suite. Actually added at the end... :)
        """
        prefix = ["", "goback.", ""]
        prefix += self.cbl_preamble('test_prog')
        prefix += self.ws
        prefix += ["procedure division."]
        prefix += self.structure_initialisation
        return self.indent_all(prefix)
    
    def test_suite_suffix_lines(self) -> List[str]:
        """
        """
        suffix = ["", "goback.", ""]
        suffix += self.sections
        return self.indent_all(suffix)
    
    def deep_equality(self, left: Tuple[str, ast.Expr], right: Tuple[str, ast.Expr]) -> str:
        """
        All tests are assertions that compare deep equality between left and right.
        """

        lvalue, ltype = left
        rvalue, rtype = right

        return_item=self.gen_data_item(self.ret_ann, self.ws)

        if type(ltype) == ast.List and type(rtype) == ast.List:
            equality_section = self.gen_equality_section(lvalue, rvalue, return_item)
            self.sections.append(equality_section)

        equality = [
            f"{lvalue} returning {return_item}.",
            f"if {return_item} = {rvalue}",
            "    display \"pass\"",
            "else",
            "    display \"fail\"",
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
    
    def gen_equality_section(self, lvalue,rvalue, return_item):
        return f"""
        check-{lvalue}-{rvalue}-equality section.
            if length of {lvalue} not equal length of {rvalue}
                move false to return-code
                exit section
            end-if
            perform varying ws-i from 1 by 1
            until ws-i > length of list-1
                if {lvalue}(ws-i) not equal {rvalue}(ws-i)
                    move false to return-code
                    exit section
                end-if
            end-perform 
            move true to {return_item}
            .
        """

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

    def gen_list(self, l: List[Tuple[str, ast.Expr]]) -> Tuple[str, ast.Expr]:
        name = self.gen_data_item(ast.List(elts=l), self.ws)

        # List Initialisation
        if len(l) != 0:
            self.structure_initialisation.append(f"*> Initialisation for {name}")
            for position, (elem, _) in enumerate(l):
                self.structure_initialisation.append(f"move {elem} to {name}({position})")

        return name, ast.List()

    def gen_list_type(self, l: List[Tuple[str, ast.Expr]]) -> str:
        elem_type = l[0][1]
        if elem_type.id in self.literal_types.keys():
            return f"{self.literal_types[elem_type.id]} occurs {len(l)}"


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