#!/usr/bin/env python3

import unittest
from stack_machine import *
from lexer import Token, LexicalAnalyzer
from parser import Parser


class TestParser(unittest.TestCase):
    def test_000(self):
        prog = '''
        a(b(c(d())))
        '''
        lex = LexicalAnalyzer(prog)
        lex.analyze()
        parser = Parser(lex)
        ast = parser.parse_expression([{}])
        calls = []
        ast.extract_calls(0, calls)
        print(calls)

    def test_001(self):
        prog = '''
        poyo[a()][b()][c(d())]
        '''
        lex = LexicalAnalyzer(prog)
        lex.analyze()
        parser = Parser(lex)
        table = {
            'poyo': {'type': 'array', 'shape': [1,1,1]}
        }
        ast = parser.parse_expression([table])
        calls = []
        ast.extract_calls(0, calls)
        print(calls)

    def test_002(self):
        prog = '''
        a() - b() / c()
        '''
        lex = LexicalAnalyzer(prog)
        lex.analyze()
        parser = Parser(lex)
        table = {}
        ast = parser.parse_expression([table])
        calls = []
        ast.extract_calls(0, calls)
        print(calls)

    def test_003(self):
        prog = '''
        poyo[g()][a() - b(d() + h()) / c() + e()][f()]
        '''
        lex = LexicalAnalyzer(prog)
        lex.analyze()
        parser = Parser(lex)
        table = {
            'poyo': {'type': 'array', 'shape': [1,1,1]}
        }
        ast = parser.parse_expression([table])
        calls = []
        ast.extract_calls(0, calls)
        print(calls)
        

if __name__ == '__main__':
    unittest.main()
