#!/usr/bin/env python3

import sys
from enum import IntEnum, auto
from lexical_analyzer import Token, LexicalAnalyzer


class Parser:
    def __init__(self, lexer):
        self.lexer = lexer

    def parse_program(self):
        return self.parse_statement_list()

    def parse_statement_list(self):
        statements = []
        while self.lexer.peek()['type'] not in [Token.EOF, Token.RBRACE]:
            statements.append(self.parse_statement())
        return {'type': 'statement_list', 'body': statements}

    def parse_statement(self):
        if self.lexer.peek()['type'] == Token.KW_WHILE:
            statement = self.parse_statement_while()
            return statement
        elif self.lexer.peek()['type'] == Token.KW_IF:
            statement = self.parse_statement_if()
            return statement
        else:
            self.expect(Token.ID)
            if self.lexer.peek()['type'] == Token.LPAREN:
                self.lexer.unseek()
                call = self.parse_inline_function_call()
                self.expect(Token.SEMICOLON)
                return call
            else: # assign
                self.lexer.unseek()
                assign = self.parse_assignment()
                self.expect(Token.SEMICOLON)
                return assign

    def parse_statement_if(self):
        self.expect(Token.KW_IF)
        self.expect(Token.LPAREN)
        condition = self.parse_expression()
        self.expect(Token.RPAREN)
        self.expect(Token.LBRACE)
        body_then = self.parse_statement_list()
        self.expect(Token.RBRACE)
        body_else = None
        if self.lexer.peek()['type'] == Token.KW_ELSE:
            self.lexer.seek()
            self.expect(Token.LBRACE)
            then_body = self.parse_statement_list()
            self.expect(Token.RBRACE)
        return {
            'type': 'if',
            'condition': condition,
            'then': body_then,
            'else': body_else,
        }

    def parse_statement_while(self):
        self.expect(Token.KW_WHILE)
        self.expect(Token.LPAREN)
        condition = self.parse_expression()
        self.expect(Token.RPAREN)
        self.expect(Token.LBRACE)
        body = self.parse_statement_list()
        self.expect(Token.RBRACE)
        return {
            'type': 'while',
            'condition': condition,
            'body': body,
        }

    def parse_inline_function_call(self):
        function_name = self.lexer.peek()['token']
        self.expect(Token.ID)
        self.expect(Token.LPAREN)
        arguments = []
        if not self.match(Token.RPAREN):
            while True:
                arguments.append(self.parse_expression())
                if not self.match(Token.COMMA):
                    break
            self.expect(Token.RPAREN)
        return {
            'type': 'inline_function_call',
            'name': function_name,
            'arguments': arguments
        }

    def parse_assignment(self):
        left_expression = self.parse_left_expression()
        if left_expression['type'] == 'array_element' and \
           self.lexer.peek()['type'] == Token.SEMICOLON:
            return {
                'type': 'array_initialization',
                'name': left_expression['name'],
                'size': left_expression['index']
            }
        right_expression = None
        for token_type in [Token.ASSIGN, Token.ADDASSIGN, Token.SUBASSIGN,
                           Token.MULASSIGN, Token.DIVASSIGN, Token.MODASSIGN]:
            try:
                self.expect(token_type)
                right_expression = self.parse_expression()
                break
            except SyntaxError as e:
                continue
        if not right_expression:
            raise SyntaxError(f'No matching assignment operators for {self.lexer.peek()}.')
        opmode = {
            Token.ASSIGN: None,
            Token.ADDASSIGN: '+',
            Token.SUBASSIGN: '-',
            Token.MULASSIGN: '*',
            Token.DIVASSIGN: '/',
            Token.MODASSIGN: '%',
        }[token_type]
        return {
            'type': 'assign',
            'mode': opmode,
            'left': left_expression,
            'right': right_expression
        }

    def parse_left_expression(self):
        token = self.lexer.peek()
        if token['type'] == Token.ID:
            self.lexer.seek()
            if self.lexer.peek()['type'] == Token.LBRACK:
                self.lexer.seek()
                index_expr = self.parse_expression()
                self.expect(Token.RBRACK)
                return {'type': 'array_element', 'name': token['token'], 'index': index_expr}
            elif self.lexer.peek()['type'] == Token.LPAREN:
                self.lexer.unseek()
                return None
            else:
                return {'type': 'variable', 'name': token['token']}

    def parse_expression(self):
        return self.parse_logical_or_expression()

    def parse_logical_or_expression(self):
        left = self.parse_logical_and_expression()
        while self.lexer.peek()['type'] == Token.OR:
            operator = self.lexer.peek()
            self.lexer.seek()
            right = self.parse_logical_and_expression()
            left = {'type': 'logical', 'operator': operator['token'], 'left': left, 'right': right}
        return left

    def parse_logical_and_expression(self):
        left = self.parse_equality_expression()
        while self.lexer.peek()['type'] == Token.AND:
            operator = self.lexer.peek()
            self.lexer.seek()
            right = self.parse_equality_expression()
            left = {'type': 'logical', 'operator': operator['token'], 'left': left, 'right': right}
        return left

    def parse_equality_expression(self):
        left = self.parse_relational_expression()
        while self.lexer.peek()['type'] in [Token.EQ, Token.NEQ]:
            operator = self.lexer.peek()
            self.lexer.seek()
            right = self.parse_relational_expression()
            left = {'type': 'logical', 'operator': operator['token'], 'left': left, 'right': right}
        return left

    def parse_relational_expression(self):
        left = self.parse_additive_expression()
        while self.lexer.peek()['type'] in [Token.LT, Token.GT, Token.LE, Token.GE]:
            operator = self.lexer.peek()
            self.lexer.seek()
            right = self.parse_additive_expression()
            left = {'type': 'logical', 'operator': operator['token'], 'left': left, 'right': right}
        return left

    def parse_additive_expression(self):
        left = self.parse_multiplicative_expression()
        while self.lexer.peek()['type'] in [Token.PLUS, Token.MINUS]:
            operator = self.lexer.peek()
            self.lexer.seek()
            right = self.parse_multiplicative_expression()
            left = {'type': 'logical', 'operator': operator['token'], 'left': left, 'right': right}
        return left

    def parse_multiplicative_expression(self):
        left = self.parse_unary_expression()
        while self.lexer.peek()['type'] in [Token.STAR, Token.SLASH, Token.PERCENT]:
            operator = self.lexer.peek()
            self.lexer.seek()
            right = self.parse_unary_expression()
            left = {'type': 'logical', 'operator': operator['token'], 'left': left, 'right': right}
        return left

    def parse_unary_expression(self):
        if self.lexer.peek()['type'] in [Token.PLUS, Token.MINUS, Token.NOT]:
            operator = self.lexer.peek()
            self.lexer.seek()
            operand = self.parse_unary_expression()
            return {'type': 'unary', 'operator': operator['token'], 'operand': operand}
        else:
            return self.parse_primary_expression()

    def parse_primary_expression(self):
        if self.lexer.peek()['type'] == Token.ID:
            token = self.lexer.peek()
            self.lexer.seek()
            if self.lexer.peek()['type'] == Token.LPAREN:
                self.lexer.unseek()
                return self.parse_inline_function_call()
            elif self.lexer.peek()['type'] == Token.LBRACK:
                self.lexer.seek()
                index_expr = self.parse_expression()
                self.expect(Token.RBRACK)
                return {'type': 'array_element', 'name': token['token'], 'index': index_expr}
            else:
                return {'type': 'variable', 'name': token['token']}
        elif self.lexer.peek()['type'] == Token.INT:
            value = self.lexer.peek()['val']
            self.lexer.seek()
            return {'type': 'integer', 'value': value}
        elif self.lexer.peek()['type'] == Token.CHAR:
            value = self.lexer.peek()['val']
            self.lexer.seek()
            return {'type': 'character', 'value': value}
        elif self.lexer.peek()['type'] == Token.LPAREN:
            self.lexer.seek()
            expr = self.parse_expression()
            self.expect(Token.RPAREN)
            return expr
        else:
            raise SyntaxError(f"Unexpected token: {self.lexer.peek()}.")

    def expect(self, token_type):
        token = self.lexer.peek()
        if token['type'] == token_type:
            self.lexer.seek()
        else:
            raise SyntaxError(f"Expected {repr(token_type)}, got {repr(token['type'])} in line {token['line'] + 1}.")

    def match(self, token_type):
        token = self.lexer.peek()
        if token['type'] == token_type:
            self.lexer.seek()
            return True
        return False

if __name__ == '__main__':
    import sys
    with open(sys.argv[1]) as f:
        prog = f.read()
    lex = LexicalAnalyzer(prog)
    lex.analyze()
    parser = Parser(lex)
    print(parser.parse_program())
