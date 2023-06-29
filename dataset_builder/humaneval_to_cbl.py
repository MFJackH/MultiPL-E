# This script translates problems from the OpenAI HumanEval dataset into COBOL.
import re
import ast
from typing import List, Dict, Tuple
import enum

DOCSTRING_LINESTART_RE = re.compile("""\n(\s+)""")

class DataItemUsage(enum.Enum):
    PARAMETER = 0
    RETURN = 1
    EXPECTED = 2

class CobolDataItem:
    
    def __init__(self, list=False):
        self.is_list = list
    
class Translator:
    
    cols="       "
    
    stop=["\ngoback."]

    prefix_last=True

    def __init__(self):
        # Used to provide unique names to storage items
        self.value_type = ["input", "output", "expected"]
        self.data_item_usage = DataItemUsage.PARAMETER
        self.assert_offset = 1

        self.ws = []
        self.list_dict = {}
        self.ws_count=1;
        self.structure_initialisation=[]
        self.sections = []
        self.literal_types = {
            "bool": "pic x comp-x",
            "int": "pic x(4) comp-x",
            "float": "pic 9(9)v99",
            "str": "pic x(256)",
            "idx": "pic 9(4)"
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
    
    def gen_data_item_type(self, id, storage_area, type=None) -> CobolDataItem:
        item = CobolDataItem()
        usage_type = self.get_usage_type()
        test_case = self.get_test_case_id()
        item.name = f"{test_case}-{usage_type}-{id}-{self.ws_count}"

        if type is None:
            type = self.literal_types[id]

        item.type = type

        storage_area.append(f"01 {item.name} {item.type}.")
        self.ws_count += 1
        return item 
    
    def gen_list_data_item(self, id, storage_area, prefix="list") -> CobolDataItem:
        item = CobolDataItem(list=True)
        idx = CobolDataItem()
        usage_type = self.get_usage_type()
        test_case = self.get_test_case_id()

        idx.name = f"{test_case}-{usage_type}-idx-{self.ws_count}"
        idx.type = self.literal_types["idx"]

        item.name = f"{test_case}-{usage_type}-list-{self.ws_count}"
        item.type = self.literal_types[id]
        item.data = f"{item.name}-data"
        item.idx = idx

        self.ws_count += 1

        storage_area.append(f"01 {item.name}.")
        storage_area.append(f"  03 {idx.name} {idx.type}.")
        storage_area.append(f"  03 {item.data} {item.type} occurs 1000 depending on {idx.name}.")
        return item
    
    def gen_data_item(self, ann: ast.expr, storage_area) -> CobolDataItem:
        if ann == None:
            raise Exception(f"No annotation")
        
        match ann:
            case ast.Name(id="Any"):
                    raise Exception(f"Type 'any' is not supported")
            case ast.Name(id=_):
                return self.gen_data_item_type(ann.id, storage_area)
            case ast.Tuple():
                elem_type = ann.elts[0][1] if len(ann.elts) != 0 else ast.Name(id="bool")
                return self.gen_list_data_item(elem_type.id, storage_area)
            case ast.List(elts=_):
                elem_type = ann.elts[0][1] if len(ann.elts) != 0 else ast.Name(id="bool")
                return self.gen_list_data_item(elem_type.id, storage_area)
            case ast.Subscript(value=ast.Name(id="List"), slice=elem_type):
                if isinstance(elem_type, ast.Subscript):
                    raise Exception(f"Nested lists are not supported")
                return self.gen_list_data_item(elem_type.id, storage_area)
            case ast.Subscript(value=ast.Name(id="Tuple"), slice=elem_type):
                # Tuples are just lists
                return self.gen_list_data_item(elem_type.elts[0].id, storage_area, prefix="tuple")
            case ast.Subscript(value=ast.Name(id="Dict"), slice=elem_type):
                raise Exception(f"Dicts do not exist in COBOL.")
            case ast.Subscript(value=ast.Name(id="Optional"), slice=elem_type):
                raise Exception(f"Optional does not exist in COBOL.")
            case ast.Subscript(value=ast.Name(id="Union"), slice=elem_type):
                raise Exception(f"Union does not exist in COBOL.")
        raise Exception(f"Unhandled annotation: {ann}")

    def translate_prompt(self, name: str, args: List[ast.arg], _returns, description: str) -> str:
        # Set up globals
        self.ws_count = 1
        self.ws = []
        self.structure_initialisation = []
        self.entry_point = name
        self.ret_ann = _returns
        # Do stuff
        cbl_description = "*>" + re.sub(DOCSTRING_LINESTART_RE, "\n*> ", description.strip()) + "\n"
        arg_list = ""
        prompt_lk = []
        on_entry_help_text = []
        on_return_help_text = []

        for arg in args:
            data_item = self.gen_data_item(arg.annotation, prompt_lk)
            on_entry_help_text.append(f"*> {data_item.name} is received on entry.")
            arg_list += data_item.name + " "

        on_return_help_text.append(f"*> Return from program with 'goback.'")

        prompt = cbl_description.split("\n")
        prompt += on_entry_help_text
        prompt += on_return_help_text
        prompt += self.cbl_preamble(name)
        prompt += ["linkage section."] 
        # Parameters
        prompt += prompt_lk
        prompt.append(f"procedure division using by reference {arg_list[:-1]}.")

        self.ws_count=1
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
        suffix += ["end program test_prog."]
        return self.indent_all(suffix)
    
    def deep_equality(self, left: Tuple[str, ast.Expr], right: Tuple[str, ast.Expr]) -> str:
        """
        All tests are assertions that compare deep equality between left and right.
        """

        lvalue, ltype = left
        rvalue, rtype = right

        self.data_item_usage = DataItemUsage.RETURN
        return_item=self.gen_data_item(self.ret_ann, self.ws)
        self.data_item_usage = DataItemUsage.PARAMETER

        if return_item.is_list:
            comp = self.list_dict[rvalue]
            comparison = f"if {return_item.name}(1:{return_item.idx.name}) = {comp.name}(1:{comp.idx.name})"
        else:
            comparison = f"if {return_item.name} = {rvalue}"

        equality = [
            f"{lvalue} {return_item.name}.",
            comparison,
            "    display \"pass\"",
            "else",
            "    display \"fail\"",
            "end-if"]
        return self.list_to_indent_str(equality)
    
    def gen_call(self, func: str, args: List[str]) -> Tuple[str, None]:
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

        return self.list_to_indent_str([f"call \"{func_name}\" using by reference {arg_list}"]), None
    
    def gen_literal(self, c: bool | str | int | float) -> Tuple[str, ast.Name]:
        """Translate a literal expression
        c: is the literal value
        """
        if type(c) == bool:
            if c:
                return "1", ast.Name("bool")
            else:
                return "0", ast.Name("bool")
        elif type(c) == str:
            c = c.replace('\n','\\n')
            return f'"{c}"', ast.Name("str")
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
        item = self.gen_data_item(ast.List(elts=l), self.ws)

        if len(l) != 0:
            self.structure_initialisation.append(f"*> Initialisation for {item.name}")
            self.structure_initialisation.append(f"move {len(l)} to {item.idx.name}")
            for position, (elem, _) in enumerate(l):
                self.structure_initialisation.append(f"move {elem} to {item.data}({position+1})")

        self.list_dict[item.name] = item
        return item.name, ast.List()

    def gen_tuple(self, t: List[Tuple[str, ast.Expr]]) -> Tuple[str, ast.Tuple]:
        item = self.gen_data_item(ast.Tuple(elts=t), self.ws) 

        if len(t) != 0:
            self.structure_initialisation.append(f"*> Initialisation for {item.name}")
            self.structure_initialisation.append(f"move {len(t)} to {item.idx.name}")
            for position, (elem, _) in enumerate(t):
                self.structure_initialisation.append(f"move {elem} to {item.name}({position+1})")

        self.list_dict[item.name] = item
        return item.name, ast.Tuple()


    def gen_dict(self, keys: List[str], values: List[str]) -> str:
        raise Exception(f"Dicts do not exist in COBOL.")
    
    def file_ext(self):
        return "cbl"
    
    def finalize(self, expr, context):
        match context:
            case "lhs":
                return expr[0]
            case "rhs":
                return expr[0]
            case _other:
                raise Exception("bad finalize context")

    def set_usage_as_parameter(self) -> None:
        self.data_item_usage = DataItemUsage.PARAMETER

    def set_usage_as_expected(self) -> None:
        self.data_item_usage = DataItemUsage.EXPECTED

    def get_usage_type(self) -> str:
        return self.value_type[self.data_item_usage.value]

    def get_test_case_id(self) -> str:
        return f"test-case-{self.assert_offset}"
