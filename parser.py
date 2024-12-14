#!/usr/bin/env python3

import sys
from enum import IntEnum, auto
from lexer import Token, LexicalAnalyzer
from stack_machine import *


def indent(level):
    return '    ' * level


class Program:
    def __init__(self, statements, funcs):
        self.statements = statements
        self.funcs = funcs

    def string(self, level=0):
        code = ''
        for name, func in self.funcs.items():
            code += func.string(level) + '\n'
        for statement in self.statements:
            code += statement.string(level) + '\n'
        return code

    def codegen(self, debug):
        tables = [{}]
        code = ''
        sm = StackMachine()
        for st in self.statements:
            if isinstance(st, StInitVariable) or isinstance(st, StInitArray):
                code += st.allocate(sm, self.funcs, tables, debug)
            else:
                code += st.codegen(sm, self.funcs, tables, debug)
        return code


class Function:
    def __init__(self, name, args, body):
        self.name = name
        self.args = args
        self.body = body

    def string(self, level):
        code = f'{indent(level)}fn {self.name}({", ".join(arg.string(0, True) for arg in self.args)}) {{\n'
        for st in self.body:
            code += st.string(level + 1) + '\n'
        code += f'{indent(level)}}}'
        return code


class Statement:
    pass


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

    def codegen(self, sm, funcs, tables, debug):
        code = ''
        var = next((table[self.lhs.name] for table in tables[::-1] if self.lhs.name in table), None)
        assert var
        opcode = {
            Token.ASSIGN: lambda x: '',
            Token.ADDASSIGN: sm.add,
            Token.SUBASSIGN: sm.subtract,
            Token.MULASSIGN: sm.multiply,
            Token.DIVASSIGN: sm.divide,
            Token.MODASSIGN: sm.modulo,
        }[self.mode]
        if var['type'] == 'variable':
            assert isinstance(self.lhs, ExpVariable)
            if self.mode == Token.ASSIGN:
                code += self.rhs.codegen(sm, funcs, tables, debug)
            else:
                code += self.lhs.codegen(sm, funcs, tables, debug)
                code += self.rhs.codegen(sm, funcs, tables, debug)
                code += opcode(debug)
            code += sm.store_variable(var['pos'], debug)
        else:
            assert isinstance(self.lhs, ExpArrayElement)
            if self.mode == Token.ASSIGN:
                code += self.rhs.codegen(sm, funcs, tables, debug)
            else:
                code += self.lhs.codegen(sm, funcs, tables, debug)
                code += self.rhs.codegen(sm, funcs, tables, debug)
                code += opcode(debug)
            for idx in self.lhs.indices[::-1]:
                code += idx.codegen(sm, funcs, tables, debug)
            code += sm.multi_dim_store(var['pos'], var['shape'], debug)
        return code


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
        for st in self.body:
            code += st.string(level + 1) + '\n'
        code += f'{indent(level)}}}'
        return code

    def codegen(self, sm, funcs, tables, debug):
        base = sm.dp
        lvars = {}
        code = ''
        for st in self.body:
            if isinstance(st, StInitVariable) or isinstance(st, StInitArray):
                code += st.allocate(sm, funcs, tables + [lvars], debug)
        size = sm.dp - base
        code += self.cond.codegen(sm, funcs, tables + [lvars], debug)
        code += sm.begin_while(debug)
        for st in self.body:
            code += st.codegen(sm, funcs, tables + [lvars], debug)
        code += self.cond.codegen(sm, funcs, tables + [lvars], debug)
        code += sm.end_while(debug)
        code += sm.pop(size, debug)
        return code


class StIf(Statement):
    def __init__(self, cond, body_then, body_else=False):
        self.cond = cond
        self.body_then = body_then
        self.body_else = body_else

    def string(self, level):
        code = f'{indent(level)}if ({self.cond}) {{\n'
        for st in self.body_then:
            code += st.string(level + 1) + '\n'
        code += f'{indent(level)}}}'
        if self.body_else:
            code += f'else {{\n'
            for st in self.body_else:
                code += st.string(level + 1) + '\n'
            code += f'{indent(level)}}}'
        return code

    def codegen(self, sm, funcs, tables, debug):
        base = sm.dp
        lvars = {}
        code = ''
        for st in self.body_then:
            if isinstance(st, StInitVariable) or isinstance(st, StInitArray):
                code += st.allocate(sm, funcs, tables + [lvars], debug)
        if self.body_else:
            for st in self.body_else:
                if isinstance(st, StInitVariable) or isinstance(st, StInitArray):
                    code += st.allocate(sm, funcs, tables + [lvars], debug)
        size = sm.dp - base
        code += self.cond.codegen(sm, funcs, tables + [lvars], debug)
        code += sm.begin_if(debug)
        for st in self.body_then:
            code += st.codegen(sm, funcs, tables + [lvars], debug)
        code += sm.begin_else(debug)
        if self.body_else:
            for st in self.body_else:
                code += st.codegen(sm, funcs, tables + [lvars], debug)
        code += sm.end_if(debug)
        code += sm.pop(size, debug)
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
        for st in self.body:
            code += st.string(level + 1) + '\n'
        code += f'{indent(level)}}}'
        return code

    def codegen(self, sm, funcs, tables, debug):
        base = sm.dp
        lvars = {}
        code = ''
        for st in self.inits:
            if isinstance(st, StInitVariable) or isinstance(st, StInitArray):
                code += st.allocate(sm, funcs, tables + [lvars], debug)
            else:
                code += st.codegen(sm, funcs, tables + [lvars], debug)
        for st in self.body:
            if isinstance(st, StInitVariable) or isinstance(st, StInitArray):
                code += st.allocate(sm, funcs, tables + [lvars], debug)
        size = sm.dp - base
        code += self.cond.codegen(sm, funcs, tables + [lvars], debug)
        code += sm.begin_while(debug)
        for st in self.body:
            code += st.codegen(sm, funcs, tables + [lvars], debug)
        for st in self.reinits:
            code += st.codegen(sm, funcs, tables + [lvars], debug)
        code += self.cond.codegen(sm, funcs, tables + [lvars], debug)
        code += sm.end_while(debug)
        code += sm.pop(size, debug)
        return code


class StCall(Statement):
    def __init__(self, expr):
        self.expr = expr

    def string(self, level):
        return f'{indent(level)}{self.expr};'

    def builtin_putchar(self, sm, funcs, tables, debug):
        if len(self.expr.args) != 1:
            raise SyntaxError(f'Number of arguments of the built-in putchar is 1.')
        code = self.expr.args[0].codegen(sm, funcs, tables, debug)
        code += sm.put_character(debug)
        return code

    def builtin_putint(self, sm, funcs, tables, debug):
        if len(self.expr.args) != 1:
            raise SyntaxError(f'Number of arguments of the built-in putchar is 1.')
        pos = sm.dp
        code = self.expr.args[0].codegen(sm, funcs, tables, debug)
        code += sm.load_variable(pos, debug)
        code += sm.load_constant(100, debug)
        code += sm.greater_or_equal(debug)
        code += sm.begin_if(debug)
        code += sm.load_variable(pos, debug)
        code += sm.load_constant(100, debug)
        code += sm.divide(debug)
        code += sm.load_constant(48, debug)
        code += sm.add(debug)
        code += sm.put_character(debug)
        code += sm.begin_else(debug)
        code += sm.end_if(debug)
        code += sm.load_variable(pos, debug)
        code += sm.load_constant(10, debug)
        code += sm.greater_or_equal(debug)
        code += sm.begin_if(debug)
        code += sm.load_variable(pos, debug)
        code += sm.load_constant(100, debug)
        code += sm.modulo(debug)
        code += sm.load_constant(10, debug)
        code += sm.divide(debug)
        code += sm.load_constant(48, debug)
        code += sm.add(debug)
        code += sm.put_character(debug)
        code += sm.begin_else(debug)
        code += sm.end_if(debug)
        code += sm.load_variable(pos, debug)
        code += sm.load_constant(10, debug)
        code += sm.modulo(debug)
        code += sm.load_constant(48, debug)
        code += sm.add(debug)
        code += sm.put_character(debug)
        code += sm.pop(1, debug)
        return code

    def codegen(self, sm, funcs, tables, debug):
        if self.expr.name == 'putchar':
            return self.builtin_putchar(sm, funcs, tables, debug)
        elif self.expr.name == 'putint':
            return self.builtin_putint(sm, funcs, tables, debug)
        else:
            base = sm.dp
            code = self.expr.codegen(sm, funcs, tables, debug)
            code += sm.pop(sm.dp - base, debug)
            return code

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

    def codegen(self, sm, funcs, tables, debug):
        if self.rhs:
            return StAssign(ExpVariable(self.name), Token.ASSIGN, self.rhs).codegen(sm, funcs, tables, debug)
        else:
            return ''

    def allocate(self, sm, funcs, tables, debug):
        assert self.name not in tables[-1]
        tables[-1][self.name] = {'type': 'variable', 'pos': sm.dp, 'size': 1}
        code = ''
        if self.rhs:
            code += self.rhs.codegen(sm, funcs, tables, debug)
        else:
            code += sm.load_constant(0, debug)
        return code


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

    def eval_shape(self):
        return [dim.evaluate() for dim in self.shape]

    def totalsize(self):
        shape = self.eval_shape()

        def rec(shape, dim):
            if len(shape) - 1 == dim:
                return shape[dim] + 4
            else:
                return (rec(shape, dim + 1) + 1) * shape[dim]
            return rec(shape, dim)

        return rec(shape, 0)

    def codegen(self, sm, funcs, tables, debug):
        return ''

    def allocate(self, sm, funcs, tables, debug):
        assert self.name not in tables[-1]
        code = sm.push_multi_dim_array(self.eval_shape(), debug)
        tables[-1][self.name] = {'type': 'array', 'pos': sm.dp, 'size': self.totalsize(), 'shape': self.eval_shape()}
        return code


class Expression:
    pass


class ExpCall(Expression):
    def __init__(self, name, args):
        self.name = name
        self.args = args

    def __str__(self):
        return f'{self.name}({", ".join(str(arg) for arg in self.args)})'

    def builtin_getchar(self, sm, funcs, tables, debug):
        return sm.get_character(debug)

    def builtin_getint(self, sm, funcs, tables, debug):
        code = ''
        ret_pos = sm.dp
        code += sm.load_constant(0, debug)
        inp_pos = sm.dp
        code += sm.load_constant(0, debug)
        code += sm.load_constant(1, debug)
        code += sm.begin_while(debug)
        code += sm.load_variable(ret_pos, debug)
        code += sm.load_constant(10, debug)
        code += sm.multiply(debug)
        code += sm.load_variable(inp_pos, debug)
        code += sm.add(debug)
        code += sm.store_variable(ret_pos, debug)
        code += sm.get_character(debug)
        code += sm.load_constant(48, debug)
        code += sm.subtract(debug)
        code += sm.store_variable(inp_pos, debug)
        code += sm.load_constant(0, debug)
        code += sm.load_variable(inp_pos, debug)
        code += sm.less_or_equal(debug)
        code += sm.load_variable(inp_pos, debug)
        code += sm.load_constant(10, debug)
        code += sm.less_than(debug)
        code += sm.booland(debug)
        code += sm.end_while(debug)
        code += sm.pop(1, debug)
        return code

    def codegen(self, sm, funcs, tables, debug):
        if self.name == 'getchar':
            return self.builtin_getchar(sm, funcs, tables, debug)
        elif self.name == 'getint':
            return self.builtin_getint(sm, funcs, tables, debug)
        else:
            return NotImplemented


class ExpArrayElement(Expression):
    def __init__(self, name, indices):
        self.name = name
        self.indices = indices

    def __str__(self):
        code = f'{self.name}'
        for idx in self.indices:
            code += f'[{idx}]'
        return code

    def codegen(self, sm, funcs, tables, debug):
        arr = next((table[self.name] for table in tables[::-1] if self.name in table), None)
        assert arr
        assert arr['type'] == 'array'
        code = ''
        for idx in self.indices[::-1]:
            code += idx.codegen(sm, funcs, tables, debug)
        code += sm.multi_dim_load(arr['pos'], arr['shape'], debug)
        return code


class ExpVariable(Expression):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def codegen(self, sm, funcs, tables, debug):
        var = next((table[self.name] for table in tables[::-1] if self.name in table), None)
        assert var
        assert var['type'] == 'variable'
        return sm.load_variable(var['pos'], debug)


class ExpInteger(Expression):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

    def evaluate(self):
        return self.value

    def codegen(self, sm, funcs, tables, debug):
        return sm.load_constant(self.value, debug)


class ExpCharacter(Expression):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

    def evaluate(self):
        return self.value

    def codegen(self, sm, funcs, tables, debug):
        return sm.load_constant(self.value, debug)


class ExpLogicalOr(Expression):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __str__(self):
        return f'({self.left} | {self.right})'

    def evaluate(self):
        return int(int(self.left.evaluate()) | int(self.right.evaluate()))

    def codegen(self, sm, funcs, tables, debug):
        code = ''
        code += self.left.codegen(sm, funcs, tables, debug)
        code += self.right.codegen(sm, funcs, tables, debug)
        return code + sm.boolor(debug)


class ExpLogicalAnd(Expression):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __str__(self):
        return f'({self.left} & {self.right})'

    def evaluate(self):
        return int(int(self.left.evaluate()) & int(self.right.evaluate()))

    def codegen(self, sm, funcs, tables, debug):
        code = ''
        code += self.left.codegen(sm, funcs, tables, debug)
        code += self.right.codegen(sm, funcs, tables, debug)
        return code + sm.booland(debug)


class ExpEquality(Expression):
    def __init__(self, mode, left, right):
        self.mode = mode
        self.left = left
        self.right = right

    def __str__(self):
        op = {
            Token.EQ: '==',
            Token.NEQ: '!=',
        }[self.mode]
        return f'({self.left} {op} {self.right})'

    def evaluate(self):
        left = int(self.left.evaluate())
        right = int(self.right.evaluate())
        if self.mode == Token.EQ:
            return int(left == right)
        else:
            return int(left != right)

    def codegen(self, sm, funcs, tables, debug):
        code = ''
        code += self.left.codegen(sm, funcs, tables, debug)
        code += self.right.codegen(sm, funcs, tables, debug)
        if self.mode == Token.EQ:
            return code + sm.equal(debug)
        else:
            return code + sm.notequal(debug)


class ExpRelational(Expression):
    def __init__(self, mode, left, right):
        self.mode = mode
        self.left = left
        self.right = right

    def __str__(self):
        op = {
            Token.LT: '<',
            Token.LE: '<=',
            Token.GT: '>',
            Token.GE: '>=',
        }[self.mode]
        return f'({self.left} {op} {self.right})'

    def evaluate(self):
        left = int(self.left.evaluate())
        right = int(self.right.evaluate())
        if self.mode == Token.LT:
            return int(left < right)
        elif self.mode == Token.GT:
            return int(left > right)
        elif self.mode == Token.LE:
            return int(left <= right)
        else:  # self.mode == Token.GE:
            return int(left >= right)

    def codegen(self, sm, funcs, tables, debug):
        code = ''
        code += self.left.codegen(sm, funcs, tables, debug)
        code += self.right.codegen(sm, funcs, tables, debug)
        if self.mode == Token.LT:
            return code + sm.less_than(debug)
        elif self.mode == Token.GT:
            return code + sm.greater_than(debug)
        elif self.mode == Token.LE:
            return code + sm.less_or_equal(debug)
        else: # self.mode == Token.GE:
            return code + sm.greater_or_equal(debug)


class ExpAdditive(Expression):
    def __init__(self, mode, left, right):
        self.mode = mode
        self.left = left
        self.right = right

    def __str__(self):
        op = {
            Token.PLUS: '+',
            Token.MINUS: '-',
        }[self.mode]
        return f'({self.left} {op} {self.right})'

    def evaluate(self):
        left = int(self.left.evaluate())
        right = int(self.right.evaluate())
        if self.mode == Token.PLUS:
            return int(left + right)
        else:  # self.mode == Token.MINUS
            return int(left - right)

    def codegen(self, sm, funcs, tables, debug):
        code = ''
        code += self.left.codegen(sm, funcs, tables, debug)
        code += self.right.codegen(sm, funcs, tables, debug)
        if self.mode == Token.PLUS:
            return code + sm.add(debug)
        else: #self.mode == Token.MINUS
            return code + sm.subtract(debug)


class ExpMultiplicative(Expression):
    def __init__(self, mode, left, right):
        self.mode = mode
        self.left = left
        self.right = right

    def __str__(self):
        op = {
            Token.SATR: '*',
            Token.SLASH: '/',
            Token.PERCENT: '%',
        }[self.mode]
        return f'({self.left} {op} {self.right})'

    def evaluate(self):
        left = int(self.left.evaluate())
        right = int(self.right.evaluate())
        if self.mode == Token.STAR:
            return int(left * right)
        elif self.mode == Token.SLASH:
            return int(left // right)
        else:  # self.mode == Token.PERCENT
            return int(left % right)

    def codegen(self, sm, funcs, tables, debug):
        code = ''
        code += self.left.codegen(sm, funcs, tables, debug)
        code += self.right.codegen(sm, funcs, tables, debug)
        if self.mode == Token.STAR:
            return code + sm.multiply(debug)
        elif self.mode == Token.SLASH:
            return code + sm.divide(debug)
        else: # self.mode == Token.PERCENT
            return code + sm.modulo(debug)


class ExpUnary(Expression):
    def __init__(self, mode, operand):
        self.mode = mode
        self.operand = operand

    def __str__(self):
        op = {
            Token.MINUS: '-',
            Token.PLUS: '+',
            Token.NOT: '!',
        }[self.mode]
        return f'{op}{self.operand}'

    def evaluate(self):
        if self.mode == Token.NOT:
            return int(not bool(self.operand.evaluate()))
        elif self.mode == Token.MINUS:
            return 256 - self.operand.evaluate()
        else:  # self.mode == Token.PLUS
            return int(bool(self.operand.evaluate()))

    def codegen(self, sm, funcs, tables, debug):
        if self.mode == Token.NOT:
            return self.operand.codegen(sm, funcs, tables, debug) + sm.boolnot(debug)
        elif self.mode == Token.MINUS:
            return sm.load_constant(0, debug) + self.operand.codegen(sm, funcs, tables, debug) + sm.subtract(debug)
        else:
            return self.operand.codegen(sm, funcs, tables, debug)


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

    def parse_program(self):
        statements = []
        funcs = {}
        tables = [{}]
        while self.peek()['type'] != Token.EOF:
            if self.peek()['type'] == Token.KW_FN:
                func = self.parse_function(tables)
                funcs[func.name] = func
            else:
                statements += [self.parse_statement(tables, False)]
        self.expect(Token.EOF)
        return Program(statements, funcs)

    def parse_function(self, tables):
        self.expect(Token.KW_FN)
        if self.peek()['type'] != Token.ID:
            raise SyntaxError(f'Expected {repr(Token.ID)}, got {repr(self.peek()["type"])} in line {token["line"] + 1}.')
        funcname = self.peek()['token']
        self.seek()
        self.expect(Token.LPAREN)
        lvars = {}
        args = []
        while self.peek()['type'] != Token.RPAREN:
            if self.peek()['type'] == Token.KW_VAR:
                args += [self.parse_init_variable(tables + [lvars], tail=None, enable_init=False)]
            elif self.peek()['type'] == Token.KW_ARR:
                args += [self.parse_init_array(tables + [lvars], tail=None)]
            else:
                raise SyntaxError(f'Unexpected token {repr(Token.KW_VAR)} or {repr(Token.KW_ARR)}, got {repr(self.peek()["type"])} in line {self.peek()["line"] + 1}.')
            self.match(Token.COMMA)
        self.expect(Token.RPAREN)
        self.expect(Token.LBRACE)
        body = []
        while self.peek()['type'] != Token.RBRACE:
            body += [self.parse_statement(tables + [lvars], True)]
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

    def parse_for(self, tables, enable_return):
        self.expect(Token.KW_FOR)
        self.expect(Token.LPAREN)
        inits = []
        lvars = {}
        while self.peek()['type'] != Token.SEMICOLON:
            if self.peek()['type'] == Token.KW_VAR:
                inits += [self.parse_init_variable(tables + [lvars], tail=None, enable_init=True)]
            elif self.peek()['type'] == Token.KW_ARR:
                inits += [self.parse_init_array(tables + [lvars], tail=None)]
            else:
                raise SyntaxError(f'Expected {repr(Token.KW_VAR)} or {repr(Token.ARR)}, got {repr(self.peek()["type"])} in line {self.peek()["line"] + 1}.')
            self.match(Token.COMMA)
        self.expect(Token.SEMICOLON)
        cond = self.parse_expression(tables + [lvars])
        self.expect(Token.SEMICOLON)
        reinits = []
        while self.peek()['type'] != Token.RPAREN:
            reinits += [self.parse_assignment(tables + [lvars], tail=None)]
        self.expect(Token.RPAREN)
        self.expect(Token.LBRACE)
        body = []
        while self.peek()['type'] != Token.RBRACE:
            body += [self.parse_statement(tables + [lvars])]
        self.expect(Token.RBRACE)
        return StFor(inits, cond, reinits, body)

    def parse_while(self, tables, enable_return):
        self.expect(Token.KW_WHILE)
        cond = self.parse_expression(tables)
        self.expect(Token.LBRACE)
        lvars = {}
        body = []
        while self.peek()['type'] != Token.RBRACE:
            body += [self.parse_statement(tables + [lvars])]
        self.expect(Token.RBRACE)
        return StWhile(cond, body)

    def parse_if(self, tables, enable_return):
        self.expect(Token.KW_IF)
        cond = self.parse_expression(tables)
        self.expect(Token.LBRACE)
        body_then = []
        lvars = {}
        while self.peek()['type'] != Token.RBRACE:
            body_then += [self.parse_statement(tables + [lvars], enable_return)]
        self.expect(Token.RBRACE)
        if self.peek()['type'] == Token.KW_ELSE:
            self.seek()
            self.expect(Token.LBRACE)
            body_else = []
            while self.peek()['type'] != Token.RBRACE:
                body_else += [self.parse_statement(tables + [lvars], enable_return)]
            self.expect(Token.RBRACE)
            return StIf(cond, body_then, body_else)
        else:
            return StIf(cond, body_then)

    def parse_statement(self, tables, enable_return=False):
        if self.peek()['type'] == Token.KW_VAR:
            return self.parse_init_variable(tables)
        elif self.peek()['type'] == Token.KW_ARR:
            return self.parse_init_array(tables)
        elif self.peek()['type'] == Token.KW_IF:
            return self.parse_if(tables, enable_return)
        elif self.peek()['type'] == Token.KW_WHILE:
            return self.parse_while(tables, enable_return)
        elif self.peek()['type'] == Token.KW_FOR:
            return self.parse_for(tables, enable_return)
        elif self.peek()['type'] == Token.KW_RETURN:
            if enable_return:
                return self.parse_return(tables)
            else:
                raise SyntaxError(f'In this context, return is not available, in line {self.peek()["line"] + 1}.')
        elif self.peek()['type'] == Token.ID:
            self.seek()
            if self.peek()['type'] == Token.LPAREN:
                self.unseek()
                expr = self.parse_expcall(tables)
                self.expect(Token.SEMICOLON)
                return StCall(expr)
            else:
                self.unseek()
                return self.parse_assignment(tables)
        else:
            raise SyntaxError(f'Unexpected token {repr(self.peek()["type"])} in line {self.peek()["line"] + 1}.')


    def parse_init_variable(self, tables, tail=Token.SEMICOLON, enable_init=True):
        self.expect(Token.KW_VAR)
        if self.peek()['type'] == Token.ID:
            name = self.peek()['token']
            if tables[-1].get(name, None):
                raise SyntaxError(f'Name "{name}" is already used in this context in line {self.peek()["line"] + 1}.')
            tables[-1][name] = {'type': 'variable'}
            self.seek()
            if self.peek()['type'] == Token.ASSIGN:
                if enable_init:
                    self.seek()
                    rhs = self.parse_expression(tables)
                else:
                    raise SyntaxError(f'In this context, assign is not supported, in line {self.peek()["line"] + 1}.')
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
            tables[-1][name] = {'type':'array', 'shape': [dim.evaluate() for dim in shape]}
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
                    indices += [self.parse_expression(tables)]
                    self.expect(Token.RBRACK)
                expr = ExpArrayElement(token['token'], indices)
                var = next((table[token['token']] for table in tables[::-1] if token['token'] in table), None)
                if not var:
                    raise SyntaxError(f'Undefined array named {token["token"]} in line {token["line"] + 1}.')
                if len(var['shape']) != len(indices):
                    raise SyntaxError(f'The left-hand-side of the assign must be a reference of a single byte, in line {token["line"] + 1}.')
                return expr
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
            left = ExpEquality(operator['type'], left, right)
        return left

    def parse_relational_expression(self, tables):
        left = self.parse_additive_expression(tables)
        while self.peek()['type'] in [Token.LT, Token.GT, Token.LE, Token.GE]:
            operator = self.peek()
            self.seek()
            right = self.parse_additive_expression(tables)
            left = ExpRelational(operator['type'], left, right)
        return left

    def parse_additive_expression(self, tables):
        left = self.parse_multiplicative_expression(tables)
        while self.peek()['type'] in [Token.PLUS, Token.MINUS]:
            operator = self.peek()
            self.seek()
            right = self.parse_multiplicative_expression(tables)
            left = ExpAdditive(operator['type'], left, right)
        return left

    def parse_multiplicative_expression(self, tables):
        left = self.parse_unary_expression(tables)
        while self.peek()['type'] in [Token.STAR, Token.SLASH, Token.PERCENT]:
            operator = self.peek()
            self.seek()
            right = self.parse_unary_expression(tables)
            left = ExpMultiplicative(operator['type'], left, right)
        return left

    def parse_unary_expression(self, tables):
        if self.peek()['type'] in [Token.PLUS, Token.MINUS, Token.NOT]:
            operator = self.peek()
            self.seek()
            operand = self.parse_unary_expression(tables)
            return ExpUnary(operator['type'], operand)
        else:
            return self.parse_primary_expression(tables)

    def parse_expcall(self, tables):
        if self.peek()['type'] != Token.ID:
            raise SyntaxError(f'Expected {repr(Token.ID)}, got {repr(self.peek()["type"])} in line {token["line"] + 1}.')
        token = self.peek()
        self.seek()
        self.expect(Token.LPAREN)
        args = []
        while self.peek()['type'] != Token.RPAREN:
            args += [self.parse_expression(tables)]
            self.match(Token.COMMA)
        self.expect(Token.RPAREN)
        return ExpCall(token['token'], args)


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
                self.unseek()
                return self.parse_expcall(tables)
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
    debug = True
    with open(sys.argv[1]) as f:
        prog = f.read()
    lex = LexicalAnalyzer(prog)
    lex.analyze()
    parser = Parser(lex)
    ast = parser.parse_program()
    print(f'[\n{ast.string(0)}]')
    print(ast.codegen(debug))
