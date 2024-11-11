#!/usr/bin/env python3

import sys
from enum import IntEnum, auto
from lexical_analyzer import Token, LexicalAnalyzer
from stack_machine import *


def indent(level):
    return '    ' * level


class SemanticError(SyntaxError):
    pass


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

    def codegen(self, sm, tables, debug=False):
        code = ''
        for st in self.body:
            code += st.codegen(sm, tables, debug)
        return code


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

    def codegen(self, sm, tables, debug=False):
        code = self.condition.codegen(sm, tables, debug)
        code += sm.begin_if(debug)
        code += self.body_then.codegen(sm, tables, debug)
        code += sm.begin_else(debug)
        if self.body_else:
            code += self.body_else.codegen(sm, tables, debug)
        code += sm.end_if(debug)
        return code


class StWhile(Statement):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

    def string(self, level):
        s = indent(level) + f'while ({self.condition}) {{\n'
        s += self.body.string(level + 1)
        s += indent(level) + '}\n'
        return s

    def codegen(self, sm, tables, debug=False):
        scope, code = self.analyze_scope_variables(sm, tables, debug)
        size = sum(var['size'] for name, var in scope.items())
        code += self.condition.codegen(sm, tables, debug)
        tables += [scope]
        code += sm.begin_while(debug)
        code += self.body.codegen(sm, tables, debug)
        code += self.condition.codegen(sm, tables, debug)
        code += sm.end_while(debug)
        code += sm.pop(size, debug)
        tables.pop()
        return code

    def analyze_scope_variables(self, sm, tables, debug):
        scope = {}
        code = ''
        for statement in self.body.body:
            if isinstance(statement, StAssign):
                name = statement.left.name
                var = next((table[name] for table in tables[::-1] if name in table), None)
                if not var:
                    scope[name] = {'type': 'variable', 'pos': sm.dp, 'size': 1}
                    code += sm.load_constant(0, debug)
            elif isinstance(statement, StArrayInit):
                name = statement.name
                arr = next((table[name] for table in tables[::-1] if name in table), None)
                if arr:
                    raise SemanticError(f'Array "{name}" is already exists.')
                size = statement.size.evaluate()
                scope[name] = {'type': 'array', 'pos': sm.dp + size, 'size': size}
                code += statement.allocate(sm, debug)
        return scope, code


class StAssign(Statement):
    def __init__(self, mode, left, right):
        self.mode = mode
        self.left = left
        self.right = right

    def string(self, level):
        return f'{indent(level)}{self.left} {self.mode} {self.right};\n'

    def codegen(self, sm, tables, debug=False):
        code = ''
        var = next((table[self.left.name] for table in tables[::-1] if self.left.name in table), None)
        if isinstance(self.left, ExpVariable):
            if var:
                # store
                if self.mode == '+=':
                    code += sm.load_variable(var['pos'], debug)
                    code += self.right.codegen(sm, tables, debug)
                    code += sm.add(debug)
                    code += sm.store_variable(var['pos'], debug)
                elif self.mode == '-=':
                    code += sm.load_variable(var['pos'], debug)
                    code += self.right.codegen(sm, tables, debug)
                    code += sm.subtract(debug)
                    code += sm.store_variable(var['pos'], debug)
                elif self.mode == '*=':
                    code += sm.load_variable(var['pos'], debug)
                    code += self.right.codegen(sm, tables, debug)
                    code += sm.multiply(debug)
                    code += sm.store_variable(var['pos'], debug)
                elif self.mode == '/=':
                    code += sm.load_variable(var['pos'], debug)
                    code += self.right.codegen(sm, tables, debug)
                    code += sm.divide(debug)
                    code += sm.store_variable(var['pos'], debug)
                elif self.mode == '%=':
                    code += sm.load_variable(var['pos'], debug)
                    code += self.right.codegen(sm, tables, debug)
                    code += sm.modulo(debug)
                    code += sm.store_variable(var['pos'], debug)
                else:  # self.mode == '=':
                    code += self.right.codegen(sm, tables, debug)
                    code += sm.store_variable(var['pos'], debug)
            else:
                # new
                if self.mode != '=':
                    raise SemanticError(f'Undefined variable: {self.name}')
                tables[-1][self.left.name] = {'type': 'variable', 'pos': sm.dp, 'size': 1}
                code += self.right.codegen(sm, tables, debug)
        else:  # isinstance(self.left, ArrayElement):
            # store only
            if not var:
                raise SemanticError(f'Undefined array: {self.left.name}')
            if var['type'] != 'array':
                raise SemanticError(f'"{self.left.name}" is not an array.')
            code += self.right.codegen(sm, tables, debug)
            code += self.left.index.codegen(sm, tables, debug)
            code += sm.store_address(var['pos'], debug)
        return code


class StArrayInit(Statement):
    def __init__(self, name, size):
        self.name = name
        self.size = size

    def string(self, level):
        return f'{self.name}[{self.size}];\n'

    def codegen(self, sm, tables, debug=False):
        array = tables[-1][self.name]
        begin = array['pos'] - array['size']
        end = array['pos'] + 4
        code = sm.clean(begin, end, debug)
        return code

    def allocate(self, sm, debug=False):
        size = self.size.evaluate()
        code = sm.push_array(size, debug)
        return code


class StCall(Statement):
    def __init__(self, name, args):
        self.expr = ExpCall(name, args)

    def string(self, level):
        return f'{indent(level)}{self.expr};\n'

    def codegen(self, sm, tables, debug=False):
        begin = sm.dp
        code = self.expr.codegen(sm, tables, debug)
        end = sm.dp
        assert begin <= end
        code += sm.pop(end - begin, debug)
        return code


class Expression:
    pass


class ExpCall(Expression):
    def __init__(self, name, args):
        self.name = name
        self.args = args

    def __str__(self):
        return f'{self.name}({", ".join(map(str, self.args))})'

    def inline_putchar(self, sm, tables, debug=False):
        if len(self.args) != 1:
            raise SemanticError(f'Inline function "putchar" takes only one argument, but entered "{self.args}".')
        code = ''
        code += self.args[0].codegen(sm, tables, debug)
        code += sm.put_character(debug)
        return code

    def inline_getchar(self, sm, tables, debug=False):
        if self.args:
            raise SemanticError(f'Inline function "getchar" takes no arguments, but entered "{self.args}"')
        return sm.get_character(debug)

    def inline_putint(self, sm, tables, debug=False):
        if len(self.args) != 1:
            raise SemanticError(f'Inline function "putint" takes only one argument, but entered "{self.args}".')
        target = sm.dp
        code = self.args[0].codegen(sm, tables, debug)
        code += sm.load_variable(target, debug)
        code += sm.load_constant(100, debug)
        code += sm.greater_or_equal(debug)
        code += sm.begin_if(debug)
        code += sm.load_variable(target, debug)
        code += sm.load_constant(100, debug)
        code += sm.divide(debug)
        code += sm.load_constant(ord('0'), debug)
        code += sm.add(debug)
        code += sm.put_character(debug)
        code += sm.begin_else(debug)
        code += sm.end_if(debug)

        code += sm.load_variable(target, debug)
        code += sm.load_constant(10, debug)
        code += sm.greater_or_equal(debug)
        code += sm.begin_if(debug)
        code += sm.load_variable(target, debug)
        code += sm.load_constant(100, debug)
        code += sm.modulo(debug)
        code += sm.load_constant(10, debug)
        code += sm.divide(debug)
        code += sm.load_constant(ord('0'), debug)
        code += sm.add(debug)
        code += sm.put_character(debug)
        code += sm.begin_else(debug)
        code += sm.end_if(debug)

        code += sm.load_constant(10, debug)
        code += sm.modulo(debug)
        code += sm.load_constant(ord('0'), debug)
        code += sm.add(debug)
        code += sm.put_character(debug)
        return code

    def inline_getint(self, sm, tables, debug=False):
        if self.args:
            raise SemanticError(f'Inline function "getint" takes no arguments, but entered "{self.args}"')
        pos = sm.dp
        code = sm.load_constant(0, debug)
        code += sm.load_constant(1, debug)
        code += sm.begin_while(debug)
        target = sm.dp
        code += sm.get_character(debug)
        code += sm.load_variable(target, debug)
        code += sm.load_constant(ord('\n'), debug)
        code += sm.notequal(debug)
        code += sm.begin_if(debug)
        code += sm.load_variable(pos, debug)
        code += sm.load_constant(10, debug)
        code += sm.multiply(debug)
        code += sm.load_variable(target, debug)
        code += sm.load_constant(ord('0'), debug)
        code += sm.subtract(debug)
        code += sm.add(debug)
        code += sm.store_variable(pos, debug)
        code += sm.begin_else(debug)
        code += sm.end_if(debug)
        code += sm.load_constant(ord('\n'), debug)
        code += sm.notequal(debug)
        code += sm.end_while(debug)
        return code

    def inline_swap(self, sm, tables, debug=False):
        if len(self.args) != 2:
            raise SemanticError(f'Inline function "swap" takes two arguments, but entered "{self.args}"')
        if (
            not isinstance(self.args[0], ExpVariable)
            and not isinstance(self.args[0], ExpArrayElement)
            or not isinstance(self.args[1], ExpVariable)
            and not isinstance(self.args[1], ExpArrayElement)
        ):
            raise SemanticError(f'Arguments of "swap" must be an instance of "ExpVariable" or "ExpArrayElement"')
        first = next((table[self.args[0].name] for table in tables[::-1] if self.args[0].name in table), None)
        second = next((table[self.args[1].name] for table in tables[::-1] if self.args[1].name in table), None)
        if not first:
            raise SemanticError(f'Undefined variable/array: {self.args[0].name}')
        if not second:
            raise SemanticError(f'Undefined variable/array: {self.args[1].name}')
        code = self.args[0].codegen(sm, tables, debug)
        code += self.args[1].codegen(sm, tables, debug)
        if isinstance(self.args[0], ExpVariable):
            code += sm.store_variable(first['pos'], debug)
        else:
            code += self.args[0].index.codegen(sm, tables, debug)
            code += sm.store_address(first['pos'], debug)
        if isinstance(self.args[1], ExpVariable):
            code += sm.store_variable(second['pos'], debug)
        else:
            code += self.args[1].index.codegen(sm, tables, debug)
            code += sm.store_address(second['pos'], debug)
        return code

    def codegen(self, sm, tables, debug=False):
        if self.name == 'putchar':
            return self.inline_putchar(sm, tables, debug)
        elif self.name == 'getchar':
            return self.inline_getchar(sm, tables, debug)
        elif self.name == 'putint':
            return self.inline_putint(sm, tables, debug)
        elif self.name == 'getint':
            return self.inline_getint(sm, tables, debug)
        elif self.name == 'swap':
            return self.inline_swap(sm, tables, debug)
        else:
            raise SyntaxError(f'No matching inline funcions: {self.name}')


class ExpArrayElement(Expression):
    def __init__(self, name, index):
        self.name = name
        self.index = index

    def __str__(self):
        return f'{self.name}[{self.index}]'

    def codegen(self, sm, tables, debug=False):
        arrelm = next((table[self.name] for table in tables[::-1] if self.name in table), None)
        if not arrelm:
            raise SemanticError(f'Undefined variable/array: {self.name}')
        if arrelm['type'] == 'variable':
            raise SemanticError(f'"{self.name}" is not an array but a variable.')
        code = self.index.codegen(sm, tables, debug)
        code += sm.load_address(arrelm['pos'], debug)
        return code


class ExpVariable(Expression):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def codegen(self, sm, tables, debug=False):
        var = next((table[self.name] for table in tables[::-1] if self.name in table), None)
        if not var:
            raise SemanticError(f'Undefined variable/array: {self.name}')
        if var['type'] != 'variable':
            raise SemanticError(f'"{self.name}" is not a variable but an array.')
        return sm.load_variable(var['pos'], debug)


class ExpInteger(Expression):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

    def evaluate(self):
        return self.value & 0xFF

    def codegen(self, sm, tables, debug=False):
        return sm.load_constant(self.value, debug)


class ExpCharacter(Expression):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(chr(self.value))

    def evaluate(self):
        return self.value & 0xFF

    def codegen(self, sm, tables, debug=False):
        return sm.load_constant(self.value, debug)


class ExpLogicalOr(Expression):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __str__(self):
        return f'({self.left} | {self.right})'

    def evaluate(self):
        return int(int(self.left.evaluate()) | int(self.right.evaluate()))

    def codegen(self, sm, tables, debug=False):
        code = ''
        code += self.left.codegen(sm, tables, debug)
        code += self.right.codegen(sm, tables, debug)
        code += sm.boolor(debug)
        return code


class ExpLogicalAnd(Expression):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __str__(self):
        return f'({self.left} & {self.right})'

    def evaluate(self):
        return int(int(self.left.evaluate()) & int(self.right.evaluate()))

    def codegen(self, sm, tables, debug=False):
        code = ''
        code += self.left.codegen(sm, tables, debug)
        code += self.right.codegen(sm, tables, debug)
        code += sm.booland(debug)
        return code


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

    def codegen(self, sm, tables, debug=False):
        code = self.left.codegen(sm, tables, debug)
        code += self.right.codegen(sm, tables, debug)
        if self.mode == '==':
            code += sm.equal(debug)
        else:
            code += sm.notequal(debug)
        return code


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

    def codegen(self, sm, tables, debug=False):
        code = self.left.codegen(sm, tables, debug)
        code += self.right.codegen(sm, tables, debug)
        if self.mode == '<':
            code += sm.less_than(debug)
        elif self.mode == '>':
            code += sm.greater_than(debug)
        elif self.mode == '<=':
            code += sm.less_or_equal(debug)
        else:  # self.mode == '>=':
            code += sm.greater_or_equal(debug)
        return code


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
            return int(left + right) & 0xFF
        else:  # self.mode == '-'
            return int(left - right) & 0xFF

    def codegen(self, sm, tables, debug=False):
        code = self.left.codegen(sm, tables, debug)
        code += self.right.codegen(sm, tables, debug)
        if self.mode == '+':
            code += sm.add(debug)
        else:  # self.mode == '-':
            code += sm.subtract(debug)
        return code


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
            return int(left * right) & 0xFF
        elif self.mode == '/':
            return int(left // right) & 0xFF
        else:  # self.mode == '%'
            return int(left % right) & 0xFF

    def codegen(self, sm, tables, debug=False):
        code = self.left.codegen(sm, tables, debug)
        code += self.right.codegen(sm, tables, debug)
        if self.mode == '*':
            code += sm.multiply(debug)
        elif self.mode == '/':
            code += sm.divide(debug)
        else:  # self.mode == '%'
            code += sm.modulo(debug)
        return code


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
            return int(not bool(self.operand.evaluate())) & 0xFF
        elif self.mode == '-':
            return (255 - self.operand.evaluate()) & 0xFF
        else:  # +
            return int(bool(self.operand.evaluate())) & 0xFF

    def codegen(self, sm, tables, debug=False):
        code = ''
        if self.mode == '!':
            code += self.operand.codegen(sm, tables, debug)
            code += sm.boolean(debug)
            code += sm.boolnot(debug)
        elif self.mode == '-':
            code += sm.load_constant(0, debug)
            code += self.operand.codegen(sm, tables, debug)
            code += sm.subtract(debug)
        else:  # self.mode == '+'
            code += self.operand.codegen(sm, tables, debug)
        return code


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
            else:  # assign
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
        if isinstance(left_expression, ExpArrayElement) and self.peek()['type'] == Token.SEMICOLON:
            return StArrayInit(left_expression.name, left_expression.index)
        right_expression = None
        token = self.peek()
        for token_type in [
            Token.ASSIGN,
            Token.ADDASSIGN,
            Token.SUBASSIGN,
            Token.MULASSIGN,
            Token.DIVASSIGN,
            Token.MODASSIGN,
        ]:
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
