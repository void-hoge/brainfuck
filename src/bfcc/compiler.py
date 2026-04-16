#!/usr/bin/env python3

from .lexer import Lexer
from .parser import Parser
from .stack_machine import StackMachine


class Compiler:
    def __init__(self, text):
        parser = Parser(Lexer(text))
        self.prog = parser.parse_program()
        self.tables = []
        self.stackmachine = StackMachine()

    def codegen(self, debug=False):
        return self.prog.codegen(debug)


def compile_source(text, debug=False):
    return Compiler(text).codegen(debug)


if __name__ == '__main__':
    from .cli import main

    raise SystemExit(main())
