#!/usr/bin/env python3

from lexer import Lexer
from parser import Parser
from stack_machine import StackMachine


class Compiler:
    def __init__(self, text):
        parser = Parser(Lexer(text))
        self.prog = parser.parse_program()
        self.tables = []
        self.stackmachine = StackMachine()

    def codegen(self, debug=False):
        return self.prog.codegen(debug)


if __name__ == '__main__':
    import sys

    with open(sys.argv[1]) as f:
        prog = f.read()
    debug = False
    comp = Compiler(prog)
    code = comp.codegen(debug)
    print(code)
