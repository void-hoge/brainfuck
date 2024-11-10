#!/usr/bin/env python3

import sys
from enum import IntEnum, auto
from lexical_analyzer import Token, LexicalAnalyzer


def indent(level):
    return '    ' * level

class Statement:
    pass

class StList(Statement):
    def __init__(self, body):
        self.body = body

    def string(self, level):
        s = ''
        for st in self.body:
            s += st.string(level)
        return s

class StIf(Statement):
    def __init__(self, condition, body_then, body_else=None):
        self.condition = condition
        self.body_then = body_then
        self.body_else = body_else

    def string(self, level):
        s = indent(level) + f'if ({self.condition}) {{\n'
        s += self.body_then.string(level + 1)
        if self.body_else == None:
            s += indent(level) + '}\n'
        else:
            s += indent(level) + '} else {\n'
            s += self.body_else.string(level + 1)
            s += indent(level) + '}\n'
        return s

class StWhile(Statement):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

    def string(self, level):
        s = indent(level) + f'while ({self.condition}) {{\n'
        s += self.body.string(level + 1)
        s += indent(level) + '}\n'
        return s

class StAssign(Statement):
    def __init__(self, mode, left, right):
        self.mode = mode
        self.left = left
        self.right = right

    def string(self, level):
        return f'{indent(level)}{self.left} {self.mode} {self.right};\n'

class StArrayInit(Statement):
    def __init__(self, name, size):
        self.name = name
        self.size = size

    def string(self, level):
        return f'{self.name}[{self.size}];\n'

class StCall(Statement):
    def __init__(self, name, args):
        self.expr = ExpCall(name, args)

    def string(self, level):
        return f'{indent(level)}{self.expr};\n'

class Expression:
    pass

class ExpCall(Expression):
    def __init__(self, name, args):
        self.name = name
        self.args = args

    def __str__(self):
        return f'{self.name}({", ".join(map(str, self.args))})'

class ExpArrayElement(Expression):
    def __init__(self, name, index):
        self.name = name
        self.index = index

    def __str__(self):
        return f'{self.name}[{self.index}]'

class ExpVariable(Expression):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

class ExpInteger(Expression):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

class ExpCharacter(Expression):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(chr(self.value))

class ExpLogicalOr(Expression):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __str__(self):
        return f'({self.left} | {self.right})'

class ExpLogicalAnd(Expression):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __str__(self):
        return f'({self.left} & {self.right})'

class ExpEquality(Expression):
    def __init__(self, mode, left, right):
        self.mode = mode
        self.left = left
        self.right = right

    def __str__(self):
        return f'({self.left} {self.mode} {self.right})'

class ExpRelational(Expression):
    def __init__(self, mode, left, right):
        self.mode = mode
        self.left = left
        self.right = right

    def __str__(self):
        return f'({self.left} {self.mode} {self.right})'

class ExpAdditive(Expression):
    def __init__(self, mode, left, right):
        self.mode = mode
        self.left = left
        self.right = right

    def __str__(self):
        return f'({self.left} {self.mode} {self.right})'

class ExpMultiplicative(Expression):
    def __init__(self, mode, left, right):
        self.mode = mode
        self.left = left
        self.right = right

    def __str__(self):
        return f'({self.left} {self.mode} {self.right})'

class ExpUnary(Expression):
    def __init__(self, mode, operand):
        self.mode = mode
        self.operand = operand

    def __str__(self):
        if self.mode:
            return f'{self.mode}{self.operand}'
        else:
            return f'{self.operand}'

class Parser:
    def __init__(self, lex):
        self.lex = lex

    def parse_program(self):
        return self.parse_statement_list()

    def parse_statement_list(self):
        statements = []
        while self.peek()['type'] not in [Token.EOF, Token.RBRACE]:
            statements.append(self.parse_statement())
        return StList(statements)

    def parse_statement(self):
        if self.peek()['type'] == Token.KW_WHILE:
            statement = self.parse_statement_while()
            return statement
        elif self.peek()['type'] == Token.KW_IF:
            statement = self.parse_statement_if()
            return statement
        else:
            self.expect(Token.ID)
            if self.peek()['type'] == Token.LPAREN:
                self.unseek()
                call = self.parse_inline_function_call(asexp=False)
                self.expect(Token.SEMICOLON)
                return call
            else: # assign
                self.unseek()
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
        if self.peek()['type'] == Token.KW_ELSE:
            self.seek()
            self.expect(Token.LBRACE)
            body_else = self.parse_statement_list()
            self.expect(Token.RBRACE)
        return StIf(condition, body_then, body_else)

    def parse_statement_while(self):
        self.expect(Token.KW_WHILE)
        self.expect(Token.LPAREN)
        condition = self.parse_expression()
        self.expect(Token.RPAREN)
        self.expect(Token.LBRACE)
        body = self.parse_statement_list()
        self.expect(Token.RBRACE)
        return StWhile(condition, body)

    def parse_inline_function_call(self, asexp=False):
        function_name = self.peek()['token']
        self.expect(Token.ID)
        self.expect(Token.LPAREN)
        arguments = []
        if not self.match(Token.RPAREN):
            while True:
                arguments.append(self.parse_expression())
                if not self.match(Token.COMMA):
                    break
            self.expect(Token.RPAREN)
        if asexp:
            return ExpCall(function_name, arguments)
        else:
            return StCall(function_name, arguments)

    def parse_assignment(self):
        left_expression = self.parse_left_expression()
        if isinstance(left_expression, ExpArrayElement) and \
           self.peek()['type'] == Token.SEMICOLON:
            return StArrayInit(left_expression.name, left_expression.index)
        right_expression = None
        token = self.peek()
        for token_type in [Token.ASSIGN, Token.ADDASSIGN, Token.SUBASSIGN,
                           Token.MULASSIGN, Token.DIVASSIGN, Token.MODASSIGN]:
            try:
                self.expect(token_type)
                right_expression = self.parse_expression()
                break
            except SyntaxError as e:
                continue
        if not right_expression:
            raise SyntaxError(f'No matching assignment operators for {self.peek()}.')
        return StAssign(token['token'], left_expression, right_expression)

    def parse_left_expression(self):
        token = self.peek()
        if token['type'] == Token.ID:
            self.seek()
            if self.peek()['type'] == Token.LBRACK:
                self.seek()
                index_expr = self.parse_expression()
                self.expect(Token.RBRACK)
                return ExpArrayElement(token['token'], index_expr)
            elif self.peek()['type'] == Token.LPAREN:
                self.unseek()
                return None
            else:
                return ExpVariable(token['token'])

    def parse_expression(self):
        return self.parse_logical_or_expression()

    def parse_logical_or_expression(self):
        left = self.parse_logical_and_expression()
        while self.peek()['type'] == Token.OR:
            operator = self.peek()
            self.seek()
            right = self.parse_logical_and_expression()
            left = ExpLogicalOr(left, right)
        return left

    def parse_logical_and_expression(self):
        left = self.parse_equality_expression()
        while self.peek()['type'] == Token.AND:
            operator = self.peek()
            self.seek()
            right = self.parse_equality_expression()
            left = ExpLogicalAnd(left, right)
        return left

    def parse_equality_expression(self):
        left = self.parse_relational_expression()
        while self.peek()['type'] in [Token.EQ, Token.NEQ]:
            operator = self.peek()
            self.seek()
            right = self.parse_relational_expression()
            left = ExpEquality(operator['token'], left, right)
        return left

    def parse_relational_expression(self):
        left = self.parse_additive_expression()
        while self.peek()['type'] in [Token.LT, Token.GT, Token.LE, Token.GE]:
            operator = self.peek()
            self.seek()
            right = self.parse_additive_expression()
            left = ExpRelational(operator['token'], left, right)
        return left

    def parse_additive_expression(self):
        left = self.parse_multiplicative_expression()
        while self.peek()['type'] in [Token.PLUS, Token.MINUS]:
            operator = self.peek()
            self.seek()
            right = self.parse_multiplicative_expression()
            left = ExpAdditive(operator['token'], left, right)
        return left

    def parse_multiplicative_expression(self):
        left = self.parse_unary_expression()
        while self.peek()['type'] in [Token.STAR, Token.SLASH, Token.PERCENT]:
            operator = self.peek()
            self.seek()
            right = self.parse_unary_expression()
            left = ExpMultiplicative(operator['token'], left, right)
        return left

    def parse_unary_expression(self):
        if self.peek()['type'] in [Token.PLUS, Token.MINUS, Token.NOT]:
            operator = self.peek()
            self.seek()
            operand = self.parse_unary_expression()
            return ExpUnary(operator['token'], operand)
        else:
            return self.parse_primary_expression()

    def parse_primary_expression(self):
        if self.peek()['type'] == Token.ID:
            token = self.peek()
            self.seek()
            if self.peek()['type'] == Token.LPAREN:
                self.unseek()
                return self.parse_inline_function_call(asexp=True)
            elif self.peek()['type'] == Token.LBRACK:
                self.seek()
                index_expr = self.parse_expression()
                self.expect(Token.RBRACK)
                return ExpArrayElement(token['token'], index_expr)
            else:
                return ExpVariable(token['token'])
        elif self.peek()['type'] == Token.INT:
            value = self.peek()['val']
            self.seek()
            return ExpInteger(value)
        elif self.peek()['type'] == Token.CHAR:
            value = self.peek()['val']
            self.seek()
            return ExpCharacter(value)
        elif self.peek()['type'] == Token.LPAREN:
            self.seek()
            expr = self.parse_expression()
            self.expect(Token.RPAREN)
            return expr
        else:
            raise SyntaxError(f"Unexpected token: {self.peek()}.")

    def seek(self):
        self.lex.seek()

    def unseek(self):
        self.lex.unseek()

    def peek(self):
        return self.lex.peek()

    def expect(self, token_type):
        token = self.peek()
        if token['type'] == token_type:
            self.seek()
        else:
            raise SyntaxError(f"Expected {repr(token_type)}, got {repr(token['type'])} in line {token['line'] + 1}.")

    def match(self, token_type):
        token = self.peek()
        if token['type'] == token_type:
            self.seek()
            return True
        return False

if __name__ == '__main__':
    import sys
    with open(sys.argv[1]) as f:
        prog = f.read()
    lex = LexicalAnalyzer(prog)
    lex.analyze()
    parser = Parser(lex)
    print(parser.parse_program().string(0))
