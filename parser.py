#!/usr/bin/env python3

import sys
from enum import IntEnum, auto
from lexer import Token, LexicalAnalyzer
from stack_machine import *


def indent(level):
    return '    ' * level


class Program:
    def __init__(self, statements, funcs, main):
        self.statements = statements
        self.funcs = funcs
        self.main = main

    def string(self, level=0):
        code = ''
        for statement in self.statements:
            code += statement.string(level) + '\n'
        for name, func in self.funcs.items():
            code += func.string(level) + '\n'
        code += self.main.string(level)
        return code


class Function:
    def __init__(self, name, args, body):
        self.name = name
        self.args = args
        self.body = body

    def string(self, level):
        code = f'{indent(level)}fn {self.name}({", ".join(arg.string(0, True) for arg in self.args)}) {{\n'
        code += self.body.string(level + 1)
        code += f'{indent(level)}}}'
        return code


class Statement:
    pass


class StList(Statement):
    def __init__(self, body):
        self.body = body

    def string(self, level):
        code = ''
        for st in self.body:
            code += st.string(level) + '\n'
        return code


class StAssign(Statement):
    def __init__(self, lhs, mode, rhs):
        self.lhs = lhs
        self.mode = mode
        self.rhs = rhs

    def string(self, level, argmode=False):
        op = {
            Token.ASSIGN: '=',
            Token.ADDASSIGN: '+=',
            Token.SUBASSIGN: '-=',
            Token.MULASSIGN: '*=',
            Token.DIVASSIGN: '/=',
            Token.MODASSIGN: '%=',
        }[self.mode]
        if argmode:
            return f'{self.lhs} {op} {self.rhs}'
        else:
            return f'{indent(level)}{self.lhs} {op} {self.rhs};'


class StReturn(Statement):
    def __init__(self, expr):
        self.expr = expr

    def string(self, level):
        return f'{indent(level)}return {self.expr};'


class StWhile(Statement):
    def __init__(self, cond, body):
        self.cond = cond
        self.body = body

    def string(self, level):
        code = f'{indent(level)}while ({self.cond}) {{\n'
        code += self.body.string(level + 1)
        code += f'{indent(level)}}}'
        return code


class StIf(Statement):
    def __init__(self, cond, body):
        self.cond = cond
        self.body = body

    def string(self, level):
        code = f'{indent(level)}if ({self.cond}) {{\n'
        code += self.body.string(level + 1)
        code += f'{indent(level)}}}'
        return code


class StFor(Statement):
    def __init__(self, inits, cond, reinits, body):
        self.inits = inits
        self.cond = cond
        self.reinits = reinits
        self.body = body

    def string(self, level):
        code = f'{indent(level)}for ('
        code += ','.join(init.string(0, True) for init in self.inits) + ';'
        code += str(self.cond) + ';'
        code += ','.join(reinit.string(0, True) for reinit in self.reinits) + ') '
        code += f'{{\n'
        code += self.body.string(level + 1)
        code += f'{indent(level)}}}'
        return code


class StCall(Statement):
    def __init__(self, expr):
        self.expr = expr

    def string(self, level):
        return f'{indent(level)}{self.expr};'


class StInitVariable(Statement):
    def __init__(self, name, rhs=None):
        self.name = name
        self.rhs = rhs

    def string(self, level, argmode=False):
        if argmode:
            if self.rhs:
                return f'var {self.name} = {self.rhs}'
            else:
                return f'var {self.name}'
        else:
            if self.rhs:
                return f'{indent(level)}var {self.name} = {self.rhs};'
            else:
                return f'{indent(level)}var {self.name};'


class StInitArray(Statement):
    def __init__(self, name, shape):
        self.name = name
        self.shape = shape

    def string(self, level, argmode=False):
        if argmode:
            code = f'arr {self.name}'
            for dim in self.shape:
                code += f'[{dim}]'
        else:
            code = f'{indent(level)}arr {self.name}'
            for dim in self.shape:
                code += f'[{dim}]'
            code += ';'
        return code


class Expression:
    pass


class ExpCall(Expression):
    def __init__(self, name, args):
        self.name = name
        self.args = args

    def __str__(self):
        return f'{self.name}({", ".join(str(arg) for arg in self.args)})'


class ExpArrayElement(Expression):
    def __init__(self, name, indices):
        self.name = name
        self.indices = indices

    def __str__(self):
        code = f'{self.name}'
        for idx in self.indices:
            code += f'[{idx}]'
        return code


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

    def evaluate(self):
        return self.value


class ExpCharacter(Expression):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(chr(self.value))

    def evaluate(self):
        return self.valure


class ExpLogicalOr(Expression):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __str__(self):
        return f'({self.left} | {self.right})'

    def evaluate(self):
        return int(int(self.left.evaluate()) | int(self.right.evaluate()))


class ExpLogicalAnd(Expression):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __str__(self):
        return f'({self.left} & {self.right})'

    def evaluate(self):
        return int(int(self.left.evaluate()) & int(self.right.evaluate()))


class ExpEquality(Expression):
    def __init__(self, mode, left, right):
        self.mode = mode
        self.left = left
        self.right = right

    def __str__(self):
        return f'({self.left} {self.mode} {self.right})'

    def evaluate(self):
        left = int(self.left.evaluate())
        right = int(self.right.evaluate())
        if self.mode == '==':
            return int(left == right)
        else:
            return int(left != right)


class ExpRelational(Expression):
    def __init__(self, mode, left, right):
        self.mode = mode
        self.left = left
        self.right = right

    def __str__(self):
        return f'({self.left} {self.mode} {self.right})'

    def evaluate(self):
        left = int(self.left.evaluate())
        right = int(self.right.evaluate())
        if self.mode == '<':
            return int(left < right)
        elif self.mode == '>':
            return int(left > right)
        elif self.mode == '<=':
            return int(left <= right)
        else:  # self.mode == '>=':
            return int(left >= right)


class ExpAdditive(Expression):
    def __init__(self, mode, left, right):
        self.mode = mode
        self.left = left
        self.right = right

    def __str__(self):
        return f'({self.left} {self.mode} {self.right})'

    def evaluate(self):
        left = int(self.left.evaluate())
        right = int(self.right.evaluate())
        if self.mode == '+':
            return int(left + right)
        else:  # self.mode == '-'
            return int(left - right)


class ExpMultiplicative(Expression):
    def __init__(self, mode, left, right):
        self.mode = mode
        self.left = left
        self.right = right

    def __str__(self):
        return f'({self.left} {self.mode} {self.right})'

    def evaluate(self):
        left = int(self.left.evaluate())
        right = int(self.right.evaluate())
        if self.mode == '*':
            return int(left * right)
        elif self.mode == '/':
            return int(left // right)
        else:  # self.mode == '%'
            return int(left % right)


class ExpUnary(Expression):
    def __init__(self, mode, operand):
        self.mode = mode
        self.operand = operand

    def __str__(self):
        if self.mode:
            return f'{self.mode}{self.operand}'
        else:
            return f'{self.operand}'

    def evaluate(self):
        if self.mode == '!':
            return int(not bool(self.operand.evaluate()))
        elif self.mode == '-':
            return 256 - self.operand.evaluate()
        else:  # +
            return int(bool(self.operand.evaluate()))


class Parser:
    def __init__(self, lex):
        self.lex = lex

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
            return token
        return False

    def parse_program(self, tables):
        statements = []
        funcs = {}
        lvars = {}
        while self.peek()['type'] != Token.EOF:
            if self.peek()['type'] == Token.KW_VAR:
                st = self.parse_init_variable(tables + [lvars])
                lvars[st.name] = {'type': 'variable'}
                statements += [st]
            elif self.peek()['type'] == Token.KW_ARR:
                st = self.parse_init_array(tables + [lvars])
                lvars[st.name] = {'type': 'array', 'shape': st.shape}
                statements += [st]
            elif self.peek()['type'] == Token.KW_FN:
                func = self.parse_function(tables + [lvars])
                funcs[func.name] = func
            else:
                raise SyntaxError(f'Unexpected token {repr(self.peek()["type"])} in line {self.peek()["line"] + 1}.')
        if not funcs.get('main', None):
            raise SyntaxError(f'The program must have a function named "main" as the starting point.')
        main = funcs.pop('main')
        if main.args != []:
            raise SyntaxError(f'The main function must not have any arguments.')
        return Program(statements, funcs, main)

    def parse_function(self, tables):
        self.expect(Token.KW_FN)
        if self.peek()['type'] != Token.ID:
            raise SyntaxError(f'Expected {Token.ID}, got {repr(self.peek()["type"])} in line {token["line"] + 1}.')
        funcname = self.peek()['token']
        self.seek()
        self.expect(Token.LPAREN)
        lvars = {}
        args = []
        while self.peek()['type'] != Token.RPAREN:
            if self.peek()['type'] == Token.KW_VAR:
                self.seek()
                if self.peek()['type'] != Token.ID:
                    raise SyntaxError(
                        f'Expected {repr(Token.ID)}, got {repr(self.peek()["type"])} in line {self.peek()["line"] + 1}.'
                    )
                name = self.peek()['token']
                if lvars.get(name, None):
                    raise SyntaxError(
                        f'Name "{name}" is already used in this context in line {self.peek()["line"] + 1}'
                    )
                self.seek()
                args += [StInitVariable(name)]
                lvars[name] = {'type': 'variable'}
            else:  # elif self.peek()['type'] == Token.KW_ARR:
                self.seek()
                if self.peek()['type'] != Token.ID:
                    raise SyntaxError(
                        f'Expected {repr(Token.ID)}, got {repr(self.peek()["type"])} in line {self.peek()["line"] + 1}.'
                    )
                name = self.peek()['token']
                if lvars.get(name, None):
                    raise SyntaxError(
                        f'Name "{name}" is already used in this contest in line {self.peek()["line"]} + 1'
                    )
                self.seek()
                shape = []
                while self.peek()['type'] == Token.LBRACK:
                    self.expect(Token.LBRACK)
                    shape += [self.parse_expression(tables)]
                    self.expect(Token.RBRACK)
                args += [StInitArray(name, shape)]
                lvars[name] = {'type': 'array', 'shape': shape}
            self.match(Token.COMMA)
        self.expect(Token.RPAREN)
        self.expect(Token.LBRACE)
        body = self.parse_statement_list(tables + [lvars])
        self.expect(Token.RBRACE)
        return Function(funcname, args, body)

    def parse_return(self, tables):
        self.expect(Token.KW_RETURN)
        expr = self.parse_expression(tables)
        self.expect(Token.KW_SEMICOLON)
        return StReturn(expr)

    def parse_assignment(self, tables, tail=Token.SEMICOLON):
        lhs = self.parse_left_expression(tables)
        if self.peek()['type'] not in [
            Token.ASSIGN,
            Token.ADDASSIGN,
            Token.SUBASSIGN,
            Token.MULASSIGN,
            Token.DIVASSIGN,
            Token.MODASSIGN,
        ]:
            raise SyntaxError(
                f'Expected {repr(Token.ASSIGN)} or the other assignment operator, got {repr(self.peek()["type"])} in line {self.peek()["line"] + 1}.'
            )
        mode = self.peek()['type']
        self.seek()
        rhs = self.parse_expression(tables)
        if tail:
            self.expect(tail)
        return StAssign(lhs, mode, rhs)

    def parse_for(self, tables):
        self.expect(Token.KW_FOR)
        self.expect(Token.LPAREN)
        inits = []
        lvars = {}
        while self.peek()['type'] != Token.SEMICOLON:
            if self.peek()['type'] == Token.KW_VAR:
                var = self.parse_init_variable(tables + [lvars], tail=None)
                lvars[var.name] = {'type': 'variable'}
                inits += [var]
            elif self.peek()['type'] == Token.KW_ARR:
                arr = self.parse_init_array(tables + [lvars], tail=None)
                lvars[arr.name] = {'type': 'array', 'shape': arr.shape}
                inits += [arr]
            else:
                assign = self.parse_assignment(tables + [lvars], tail=None)
                inits += [assign]
            self.match(Token.COMMA)
        self.expect(Token.SEMICOLON)
        cond = self.parse_expression(tables + [lvars])
        self.expect(Token.SEMICOLON)
        reinits = []
        while self.peek()['type'] != Token.RPAREN:
            reinits += [self.parse_assignment(tables + [lvars], tail=None)]
        self.expect(Token.RPAREN)
        self.expect(Token.LBRACE)
        body = self.parse_statement_list(tables + [lvars], appendmode=True)
        self.expect(Token.RBRACE)
        return StFor(inits, cond, reinits, body)

    def parse_while(self, tables):
        self.expect(Token.KW_WHILE)
        cond = self.parse_expression(tables)
        self.expect(Token.LBRACE)
        body = self.parse_statement_list(tables)
        self.expect(Token.RBRACE)
        return StWhile(cond, body)

    def parse_if(self, tables):
        self.expect(Token.KW_IF)
        cond = self.parse_expression(tables)
        self.expect(Token.LBRACE)
        body = self.parse_statement_list(tables)
        self.expect(Token.RBRACE)
        return StIf(cond, body)

    def parse_statement_list(self, tables, appendmode=False):
        if appendmode:
            lvars = tables[-1]
            tables.pop()
        else:
            lvars = {}
        statements = []
        while self.peek()['type'] != Token.RBRACE:
            if self.peek()['type'] == Token.KW_VAR:
                st = self.parse_init_variable(tables + [lvars])
                lvars[st.name] = {'type': 'variable'}
                statements += [st]
            elif self.peek()['type'] == Token.KW_ARR:
                st = self.parse_init_array(tables + [lvars])
                lvars[st.name] = {'type': 'array', 'shape': st.shape}
                statements += [st]
            elif self.peek()['type'] == Token.KW_IF:
                statements += [self.parse_if(tables + [lvars])]
            elif self.peek()['type'] == Token.KW_WHILE:
                statements += [self.parse_while(tables + [lvars])]
            elif self.peek()['type'] == Token.KW_FOR:
                statements += [self.parse_for(tables + [lvars])]
            elif self.peek()['type'] == Token.KW_RETURN:
                statements += [self.parse_return(tables + [lvars])]
            elif self.peek()['type'] == Token.ID:
                self.seek()
                if self.peek()['type'] == Token.LPAREN:
                    self.unseek()
                    token = self.peek()
                    self.seek()
                    self.expect(Token.LPAREN)
                    args = []
                    while self.peek()['type'] != Token.RPAREN:
                        args += [self.parse_expression(tables + [lvars])]
                        self.match(Token.COMMA)
                    self.expect(Token.RPAREN)
                    self.expect(Token.SEMICOLON)
                    statements += [StCall(ExpCall(token['token'], args))]
                else:
                    self.unseek()
                    statements += [self.parse_assignment(tables)]
            else:
                raise SyntaxError(f'Unexpected token {repr(self.peek()["type"])} in line {self.peek()["line"] + 1}.')
        return StList(statements)

    def parse_init_variable(self, tables, tail=Token.SEMICOLON):
        self.expect(Token.KW_VAR)
        if self.peek()['type'] == Token.ID:
            name = self.peek()['token']
            if tables[-1].get(name, None):
                raise SyntaxError(f'Name "{name}" is already used in this context in line {self.peek()["line"] + 1}.')
            self.seek()
            if self.peek()['type'] == Token.ASSIGN:
                self.seek()
                rhs = self.parse_expression(tables)
            else:
                rhs = None
        else:
            raise SyntaxError(
                f'Expected {repr(Token.ID)}, got {repr(self.peek()["type"])} in line {self.peek()["line"] + 1}.'
            )
        if tail:
            self.expect(tail)
        return StInitVariable(name, rhs)

    def parse_init_array(self, tables, tail=Token.SEMICOLON):
        self.expect(Token.KW_ARR)
        if self.peek()['type'] == Token.ID:
            name = self.peek()['token']
            if tables[-1].get(name, None):
                raise SyntaxError(f'Name "{name}" is already used in this context in line {self.peek()["line"] + 1}.')
            self.seek()
            shape = []
            while self.peek()['type'] != Token.SEMICOLON:
                self.expect(Token.LBRACK)
                shape += [self.parse_expression(tables)]
                self.expect(Token.RBRACK)
        else:
            raise SyntaxError(
                f'Expected {repr(Token.ID)}, got {repr(self.peek()["type"])} in line {self.peek()["line"] + 1}.'
            )
        if tail:
            self.expect(tail)
        return StInitArray(name, shape)

    def parse_return(self, tables):
        self.expect(Token.KW_RETURN)
        expr = self.parse_expression(tables)
        self.expect(Token.SEMICOLON)
        return StReturn(expr)

    def parse_left_expression(self, tables):
        token = self.peek()
        if token['type'] == Token.ID:
            self.seek()
            if self.peek()['type'] == Token.LBRACK:
                indices = []
                while self.peek()['type'] == Token.LBRACK:
                    self.seek()
                    indices += [self.parse_expression()]
                    self.expect(Token.RBRACK)
                return ExpArrayElement(token['token'], indices)
            else:
                return ExpVariable(token['token'])
        else:
            raise SyntaxError(
                f'Expected {repr(Token.ID)}, got {repr(self.peek()["type"])} in line {self.peek()["line"] + 1}.'
            )

    def parse_expression(self, tables):
        return self.parse_logical_or_expression(tables)

    def parse_logical_or_expression(self, tables):
        left = self.parse_logical_and_expression(tables)
        while self.peek()['type'] == Token.OR:
            operator = self.peek()
            self.seek()
            right = self.parse_logical_and_expression(tables)
            left = ExpLogicalOr(left, right)
        return left

    def parse_logical_and_expression(self, tables):
        left = self.parse_equality_expression(tables)
        while self.peek()['type'] == Token.AND:
            operator = self.peek()
            self.seek()
            right = self.parse_equality_expression(tables)
            left = ExpLogicalAnd(left, right)
        return left

    def parse_equality_expression(self, tables):
        left = self.parse_relational_expression(tables)
        while self.peek()['type'] in [Token.EQ, Token.NEQ]:
            operator = self.peek()
            self.seek()
            right = self.parse_relational_expression(tables)
            left = ExpEquality(operator['token'], left, right)
        return left

    def parse_relational_expression(self, tables):
        left = self.parse_additive_expression(tables)
        while self.peek()['type'] in [Token.LT, Token.GT, Token.LE, Token.GE]:
            operator = self.peek()
            self.seek()
            right = self.parse_additive_expression(tables)
            left = ExpRelational(operator['token'], left, right)
        return left

    def parse_additive_expression(self, tables):
        left = self.parse_multiplicative_expression(tables)
        while self.peek()['type'] in [Token.PLUS, Token.MINUS]:
            operator = self.peek()
            self.seek()
            right = self.parse_multiplicative_expression(tables)
            left = ExpAdditive(operator['token'], left, right)
        return left

    def parse_multiplicative_expression(self, tables):
        left = self.parse_unary_expression(tables)
        while self.peek()['type'] in [Token.STAR, Token.SLASH, Token.PERCENT]:
            operator = self.peek()
            self.seek()
            right = self.parse_unary_expression(tables)
            left = ExpMultiplicative(operator['token'], left, right)
        return left

    def parse_unary_expression(self, tables):
        if self.peek()['type'] in [Token.PLUS, Token.MINUS, Token.NOT]:
            operator = self.peek()
            self.seek()
            operand = self.parse_unary_expression(tables)
            return ExpUnary(operator['token'], operand)
        else:
            return self.parse_primary_expression(tables)

    def parse_primary_expression(self, tables):
        if self.peek()['type'] == Token.ID:
            token = self.peek()
            self.seek()
            if self.peek()['type'] == Token.LBRACK:
                name = token['token']
                arr = next((table[name] for table in tables[::-1] if name in table), None)
                if not arr:
                    raise SyntaxError(f'Undefined array named "{name}" in line {token["line"] + 1}.')
                if arr['type'] != 'array':
                    raise SyntaxError(f'"{name}" is not an array but a variable in line {token["line"] + 1}.')
                indices = []
                while self.peek()['type'] == Token.LBRACK:
                    self.seek()
                    indices += [self.parse_expression(tables)]
                    self.expect(Token.RBRACK)
                return ExpArrayElement(name, indices)
            elif self.peek()['type'] == Token.LPAREN:
                self.seek()
                args = []
                while self.peek()['type'] != Token.RPAREN:
                    args += [self.parse_expression(tables)]
                    self.match(Token.COMMA)
                self.expect(Token.RPAREN)
                return ExpCall(token['token'], args)
            else:
                name = token['token']
                var = next((table[name] for table in tables[::-1] if name in table), None)
                if not var:
                    raise SyntaxError(f'Undefined variable named "{name}" in line {token["line"] + 1}.')
                if var['type'] != 'variable':
                    raise SyntaxError(f'"{name}" is not a variable but an array in line {token["line"] + 1}.')
                return ExpVariable(name)
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
            expr = self.parse_expression(tables)
            self.expect(Token.RPAREN)
            return expr
        else:
            raise SyntaxError(f"Unexpected token: {self.peek()}.")


if __name__ == '__main__':
    import sys

    with open(sys.argv[1]) as f:
        prog = f.read()
    lex = LexicalAnalyzer(prog)
    lex.analyze()
    parser = Parser(lex)
    tables = []
    print(parser.parse_program(tables).string(0))
