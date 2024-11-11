#!/usr/bin/env python3

from lexical_analyzer import LexicalAnalyzer
from parser import Parser
from stack_machine import StackMachine


class Compiler:
    def __init__(self, text):
        parser = Parser(LexicalAnalyzer(text))
        self.prog = parser.parse_program()
        self.table = {}
        self.stackmachine = StackMachine()

    def codegen(self):
        return self.prog.codegen(self.stackmachine, self.table, debug=False)


if __name__ == '__main__':
    import sys

    with open(sys.argv[1]) as f:
        prog = f.read()
    comp = Compiler(prog)
    print(comp.codegen())
