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
        table = {'poyo': {'type': 'array', 'shape': [1, 1, 1]}}
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
        table = {'poyo': {'type': 'array', 'shape': [1, 1, 1]}}
        ast = parser.parse_expression([table])
        calls = []
        ast.extract_calls(0, calls)
        print(calls)

    def test_004(self):
        prog = '''
        fn func(var a) {
            var v;
            while (v) {
                if (v) {
                     func(a);
                }
            }
        }
        '''
        lex = LexicalAnalyzer(prog)
        lex.analyze()
        parser = Parser(lex)
        ast = parser.parse_program()
        print(ast.string(0))
        print(ast.funcs['func'].count_states(1))

    def test_005(self):
        prog = '''
        fn func(var a) {
            putchar(a);
        }
        func('a');
        '''
        debug = True
        lex = LexicalAnalyzer(prog)
        lex.analyze()
        parser = Parser(lex)
        ast = parser.parse_program()
        print(f'[\n{ast.string(1)}]')
        bf = ast.codegen(debug)
        print(bf)

    def test_006(self):
        prog = '''
        fn hoge(var a) {
            putchar(a);
            return 'd';
        }
        fn poyo(var p) {
            putchar(hoge(p));
            putchar(p + 3);
            return 'p';
        }
        putchar(poyo('f'));
        '''
        debug = True
        lex = LexicalAnalyzer(prog)
        lex.analyze()
        parser = Parser(lex)
        ast = parser.parse_program()
        print(f'[\n{ast.string(1)}]')
        bf = ast.codegen(debug)
        print(bf)

    def test_007(self):
        prog = '''
        fn hoge(var a) {
            putchar(a);
            if (a == 0) {
                return 0;
            }
            hoge(a - 1);
            return 0;
        }
        putchar(hoge('f'));
        '''
        debug = True
        lex = LexicalAnalyzer(prog)
        lex.analyze()
        parser = Parser(lex)
        ast = parser.parse_program()
        print(f'[\n{ast.string(1)}]')
        bf = ast.codegen(debug)
        print(bf)


if __name__ == '__main__':
    unittest.main()
