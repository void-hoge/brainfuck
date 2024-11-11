#!/usr/bin/env python3

from lexical_analyzer import LexicalAnalyzer
from parser import Parser
from stack_machine import StackMachine


class Compiler:
    def __init__(self, text):
        parser = Parser(LexicalAnalyzer(text))
        self.prog = parser.parse_program()
        self.tables = [{}]
        self.stackmachine = StackMachine()

    def codegen(self, debug=False):
        return self.prog.codegen(self.stackmachine, self.tables, debug)


if __name__ == '__main__':
    import sys
    with open(sys.argv[1]) as f:
        prog = f.read()
    debug = False
    comp = Compiler(prog)
    code = comp.codegen(debug)
    if debug:
        print(code)
    else:
        for i in range(0, len(code), 80):
            print(code[i:i+80])
