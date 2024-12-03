#!/usr/bin/env python3

import sys
from ir_lexer import Token, Lexer
from stack_machine import StackMachine


def indent(level):
    return '    ' * level


class SemanticError(SyntaxError):
    pass


class Statement:
    pass


class Program:
    def __init__(self, block):
        self.block = block

    def string(self, level):
        return self.block.string(level)

    def codegen(self, sm, tables, debug):
        return self.block.codegen(sm, tables, debug)


class StList(Statement):
    def __init__(self, body):
        self.body = body

    def string(self, level):
        code = ''
        for st in self.body:
            code += st.string(level)
        return code

    def codegen(self, sm, tables, debug):
        code = ''
        for statement in self.body:
            code += statement.codegen(sm, tables, debug)
        return code


class StWhile(Statement):
    def __init__(self, initializers, condition, body):
        self.initializers = initializers
        self.condition = condition
        self.body = body

    def string(self, level):
        code = f'{indent(level)}while {{\n'
        for init in self.initializers:
            code += init.string(level + 1)
        code += f'{indent(level)}}} {self.condition} {{\n'
        code += self.body.string(level + 1)
        code += indent(level) + f'}}\n'
        return code

    def codegen(self, sm, tables, debug):
        retpos = sm.dp
        scope = {}
        code = ''
        for init in self.initializers:
            vcode, var = init.codegen(sm, tables + [scope], debug)
            if scope.get(init.name):
                raise SemanticError(f'Variable/array named "{init.name}" already exists in the scope.')
            scope[init.name] = var
            code += vcode
        size = sm.dp - retpos
        code += self.condition.codegen(sm, tables + [scope], debug)
        code += sm.begin_while(debug)
        code += self.body.codegen(sm, tables + [scope], debug)
        code += self.condition.codegen(sm, tables + [scope], debug)
        code += sm.end_while(debug)
        code += sm.pop(size, debug)
        return code


class StIf(Statement):
    def __init__(self, initializers, condition, body_then, body_else=None):
        self.initializers = initializers
        self.condition = condition
        self.body_then = body_then
        self.body_else = body_else

    def string(self, level):
        code = f'{indent(level)}if {{\n'
        for init in self.initializers:
            code += init.string(level + 1)
        code += f'{indent(level)}}} {self.condition} {{\n'
        code += self.body_then.string(level + 1)
        code += indent(level) + f'}}'
        if self.body_else:
            code += f' else {{\n'
            code += self.body_else.string(level + 1)
            code += f'{indent(level)}}}'
        code += '\n'
        return code

    def codegen(self, sm, tables, debug):
        retpos = sm.dp
        scope = {}
        code = ''
        for init in self.initializers:
            vcode, var = init.codegen(sm, tables + [scope], debug)
            if scope.get(init.name):
                raise SemanticError(f'Variable/array named "{init.name}" already defined in the scope.')
            scope[init.name] = var
            code += vcode
        size = sm.dp - retpos
        code += self.condition.codegen(sm, tables + [scope], debug)
        code += sm.begin_if(debug)
        code += self.body_then.codegen(sm, tables + [scope], debug)
        code += sm.begin_else(debug)
        if self.body_else:
            code += self.body_else.codegen(sm, tables + [scope], debug)
        code += sm.end_if(debug)
        code += sm.pop(size, debug)
        return code


class InitVariable(Statement):
    def __init__(self, name, rhs=None):
        self.name = name
        self.rhs = rhs

    def string(self, level):
        if self.rhs:
            return f'{indent(level)}var {self.name} = {self.rhs};\n'
        else:
            return f'{indent(level)}var {self.name} = 0;\n'

    def codegen(self, sm, tables, debug):
        pos = sm.dp
        if self.rhs:
            code = self.rhs.codegen(sm, tables, debug)
        else:
            code = sm.load_constant(0, debug)
        return code, {'type': 'variable', 'pos': pos, 'size': 1}


class InitArray(Statement):
    def __init__(self, name, shape):
        self.name = name
        self.shape = shape

    def string(self, level):
        code = f'{indent(level)}arr {self.name}'
        for size in self.shape:
            code += f'[{size}]'
        return code + ';\n'

    def getshape(self):
        return [size.evaluate() for size in self.shape]

    def totalsize(self):
        shape = self.getshape()

        def rec(shape, dim):
            if len(shape) - 1 == dim:
                return shape[dim] + 4
            else:
                return (rec(shape, dim + 1) + 1) * shape[dim]
            return rec(shape, dim)

        return rec(shape, 0)

    def codegen(self, sm, tables, debug):
        code = sm.push_multi_dim_array(self.getshape(), debug)
        return code, {'type': 'array', 'pos': sm.dp, 'size': self.totalsize(), 'shape': self.getshape()}


class StAssign(Statement):
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs

    def string(self, level):
        return f'{indent(level)}{self.lhs} = {self.rhs};\n'

    def codegen(self, sm, tables, debug):
        code = self.rhs.codegen(sm, tables, debug)
        var = next((table[self.lhs.name] for table in tables[::-1] if self.lhs.name in table), None)
        if not var:
            raise SemanticError(f'Undefined array or variable named "{self.name}"')
        if var['type'] == 'variable':
            if not isinstance(self.lhs, ExpVariable):
                raise SemanticError(f'Expected a variable as lhs of assign, but "{self.lhs}" is not variable')
            code += sm.store_variable(var['pos'], debug)
        else:  # var['type'] == 'array'
            if not isinstance(self.lhs, ExpArrayElement):
                raise SemanticError(f'Expected a variable as lhs of assign, but "{self.lhs}" is not variable')

            for idx in self.lhs.indices[::-1]:
                code += idx.codegen(sm, tables, debug)
            code += sm.multi_dim_store(var['pos'], var['shape'], debug)
        return code


class StPut(Statement):
    def __init__(self, expr):
        self.expr = expr

    def string(self, level):
        return f'{indent(level)}put({self.expr});\n'

    def codegen(self, sm, tables, debug):
        code = self.expr.codegen(sm, tables, debug)
        code += sm.put_character(debug)
        return code


class StBlock(Statement):
    def __init__(self, block):
        self.block = block

    def string(self, level):
        return self.block.string(0) + ';\n'

    def codegen(self, sm, tables, debug):
        code = self.block.codegen(sm, tables, debug)
        code += sm.pop(1, debug)
        return code


class Expression:
    pass


class ExpBlock(Expression):
    def __init__(self, initializers, body, retval):
        self.initializers = initializers
        self.body = body
        self.retval = retval

    def __str__(self):
        return self.string(1)

    def string(self, level):
        code = f'{indent(level)}{{\n'
        for init in self.initializers:
            code += init.string(level + 1)
        code += f'{indent(level)}}} {{\n'
        code += self.body.string(level + 1)
        code += f'{indent(level + 1)}return {self.retval};\n'
        code += indent(level) + f'}}\n'
        return code

    def codegen(self, sm, tables, debug):
        scope = {}
        retpos = sm.dp
        code = sm.load_constant(0, debug)
        for init in self.initializers:
            vcode, var = init.codegen(sm, tables + [scope], debug)
            if scope.get(init.name):
                raise SemanticError(f'Variable/array named "{init.name}" already exists in the scope.')
            scope[init.name] = var
            code += vcode
        size = sm.dp - retpos - 1
        code += self.body.codegen(sm, tables + [scope], debug)
        code += self.retval.codegen(sm, tables + [scope], debug)
        code += sm.store_variable(retpos, debug)
        code += sm.pop(size, debug)
        return code


class ExpArrayElement(Expression):
    def __init__(self, name, indices):
        self.name = name
        self.indices = indices

    def __str__(self):
        code = f'{self.name}'
        for idx in self.indices:
            code += f'[{idx}]'
        return code

    def codegen(self, sm, tables, debug):
        elm = next((table[self.name] for table in tables[::-1] if self.name in table), None)
        if not elm:
            raise SemanticError(f'Undefined array or variable named "{self.name}"')
        if elm['type'] != 'array':
            raise SemanticError(f'"{self.name}" is not an array but a variable.')
        code = ''
        for idx in self.indices[::-1]:
            code += idx.codegen(sm, tables, debug)
        code += sm.multi_dim_load(elm['pos'], elm['shape'], debug)
        return code


class ExpVariable(Expression):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def codegen(self, sm, tables, debug):
        var = next((table[self.name] for table in tables[::-1] if self.name in table), None)
        if not var:
            raise SemanticError(f'Undefined array or variable named "{self.name}"')
        if var['type'] != 'variable':
            raise SemanticError(f'"{self.name}" is not a variable but an array.')
        return sm.load_variable(var['pos'], debug)


class ExpInteger(Expression):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

    def evaluate(self):
        return self.value

    def codegen(self, sm, tables, debug=False):
        return sm.load_constant(self.value, debug)


class ExpGet(Expression):
    def __init__(self):
        pass

    def __str__(self):
        return f'get()'

    def codegen(self, sm, tables, debug):
        return sm.get_character(debug)


class ExpLogicalOr(Expression):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __str__(self):
        return f'({self.left} | {self.right})'

    def evaluate(self):
        return int(int(self.left.evaluate()) | int(self.right.evaluate()))

    def codegen(self, sm, tables, debug):
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

    def codegen(self, sm, tables, debug):
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

    def codegen(self, sm, tables, debug):
        code = ''
        code += self.left.codegen(sm, tables, debug)
        code += self.right.codegen(sm, tables, debug)
        if self.mode == '==':
            return code + sm.equal(debug)
        else:
            return code + sm.notequal(debug)


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

    def codegen(self, sm, tables, debug):
        code = ''
        code += self.left.codegen(sm, tables, debug)
        code += self.right.codegen(sm, tables, debug)
        if self.mode == '<':
            return code + sm.less_than(debug)
        elif self.mode == '>':
            return code + sm.greater_than(debug)
        elif self.mode == '<=':
            return code + sm.less_or_equal(debug)
        else:
            return code + sm.greater_or_equal(debug)


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

    def codegen(self, sm, tables, debug):
        code = ''
        code += self.left.codegen(sm, tables, debug)
        code += self.right.codegen(sm, tables, debug)
        if self.mode == '+':
            return code + sm.add(debug)
        else:
            return code + sm.subtract(debug)


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

    def codegen(self, sm, tables, debug):
        code = ''
        code += self.left.codegen(sm, tables, debug)
        code += self.right.codegen(sm, tables, debug)
        if self.mode == '*':
            return code + sm.multiply(debug)
        elif self.mode == '/':
            return code + sm.divide(debug)
        else:
            return code + sm.modulo(debug)


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

    def codegen(self, sm, tables, debug):
        if self.mode == '!':
            return self.operand.codegen(sm, tables, debug) + sm.boolnot(debug)
        elif self.mode == '-':
            return sm.load_constant(0, debug) + self.operand.codegen(sm, tables, debug) + sm.subtract(debug)
        else:
            return self.operand.codegen(sm, tables, debug)


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
            return True
        return False

    def parse_program(self):
        block = self.parse_block_expression()
        self.expect(Token.EOF)
        return Program(block)

    def parse_statement_list(self):
        statements = []
        while self.peek()['type'] not in [Token.EOF, Token.RBRACE]:
            statements += [self.parse_statement()]
        return StList(statements)

    def parse_statement(self):
        if self.peek()['type'] == Token.KW_WHILE:
            return self.parse_while()
        elif self.peek()['type'] == Token.KW_IF:
            return self.parse_if()
        elif self.peek()['type'] == Token.ID:
            if self.peek()['token'] == 'put':
                return self.parse_put()
            else:
                return self.parse_assignment()
        elif self.peek()['type'] == Token.LBRACE:
            return self.parse_block_statement()
        else:
            raise SyntaxError(f'Unexpected token "{self.peek()["token"]}".')

    def parse_put(self):
        token = self.peek()
        self.expect(Token.ID)
        assert token['token'] == 'put'
        expr = self.parse_expression()
        self.expect(Token.SEMICOLON)
        return StPut(expr)

    def parse_while(self):
        self.expect(Token.KW_WHILE)
        self.expect(Token.LBRACE)
        initializers = self.parse_initializers()
        self.expect(Token.RBRACE)

        condition = self.parse_expression()

        self.expect(Token.LBRACE)
        body = self.parse_statement_list()
        self.expect(Token.RBRACE)
        return StWhile(initializers, condition, body)

    def parse_if(self):
        self.expect(Token.KW_IF)
        self.expect(Token.LBRACE)
        initializers = self.parse_initializers()
        self.expect(Token.RBRACE)

        condition = self.parse_expression()

        self.expect(Token.LBRACE)
        body_then = self.parse_statement_list()
        self.expect(Token.RBRACE)

        if self.peek()['type'] == Token.KW_ELSE:
            self.seek()
            self.expect(Token.LBRACE)
            body_else = self.parse_statement_list()
            self.expect(Token.RBRACE)
            return StIf(initializers, condition, body_then, body_else)
        else:
            return StIf(initializers, condition, body_then)

    def parse_while(self):
        self.expect(Token.KW_WHILE)
        self.expect(Token.LBRACE)
        initializers = self.parse_initializers()
        self.expect(Token.RBRACE)

        condition = self.parse_expression()

        self.expect(Token.LBRACE)
        body = self.parse_statement_list()
        self.expect(Token.RBRACE)
        return StWhile(initializers, condition, body)

    def parse_initializers(self):
        initializers = []
        while self.peek()['type'] in [Token.KW_VAR, Token.KW_ARR]:
            if self.peek()['type'] == Token.KW_VAR:
                initializers += [self.parse_init_variable()]
            else:
                initializers += [self.parse_init_array()]
        return initializers

    def parse_init_variable(self):
        self.expect(Token.KW_VAR)
        if self.peek()['type'] != Token.ID:
            raise SyntaxError(f'Expected ID, but there is "{self.peek()["token"]}" ({repr(self.peek()["type"])}).')
        name = self.peek()['token']
        self.seek()
        if self.peek()['type'] == Token.ASSIGN:
            self.seek()
            rhs = self.parse_expression()
            self.expect(Token.SEMICOLON)
            return InitVariable(name, rhs)
        else:
            self.expect(Token.SEMICOLON)
            return InitVariable(name)

    def parse_init_array(self):
        self.expect(Token.KW_ARR)
        if self.peek()['type'] != Token.ID:
            raise SyntaxError(f'Expected ID, but there is "{self.peek()["token"]}" ({repr(self.peek()["type"])}).')
        name = self.peek()['token']
        self.seek()
        if self.peek()['type'] == Token.LBRACK:
            indices = []
            while self.peek()['type'] == Token.LBRACK:
                self.seek()
                expr = self.parse_expression()
                size = expr.evaluate()
                if size <= 0:
                    SyntaxError(f'Each size of array\'s dimension must be larger than 0.')
                elif size > 256:
                    print(
                        f'Warning: One of the size of the array "{name}" ({expr}) is larger than 256 (inaccesible dynamically).',
                        file=sys.stderr,
                    )
                indices += [expr]
                self.expect(Token.RBRACK)
            self.expect(Token.SEMICOLON)
            return InitArray(name, indices)
        else:
            raise SyntaxError(
                f'Expected a "[", but there is a "{self.peek()["token"]}" ({repr(self.peek()["type"])}).'
            )

    def parse_assignment(self):
        lhs = self.parse_left_expression()
        self.expect(Token.ASSIGN)
        rhs = self.parse_expression()
        self.expect(Token.SEMICOLON)
        return StAssign(lhs, rhs)

    def parse_left_expression(self):
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

    def parse_block_statement(self):
        block = self.parse_block_expression()
        self.expect(Token.SEMICOLON)
        return StBlock(block)

    def parse_expression(self):
        return self.parse_logical_or_expression()

    def parse_block_expression(self):
        self.expect(Token.LBRACE)
        initializers = self.parse_initializers()
        self.expect(Token.RBRACE)
        self.expect(Token.LBRACE)
        body = []
        while self.peek()['type'] not in [Token.RBRACE, Token.KW_RETURN]:
            body += [self.parse_statement()]
        if self.peek()['type'] == Token.KW_RETURN:
            self.seek()
            retval = self.parse_expression()
            self.expect(Token.SEMICOLON)
        else:
            retval = ExpInteger(0)
        self.expect(Token.RBRACE)
        return ExpBlock(initializers, StList(body), retval)

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
            if token['token'] == 'get':
                self.expect(Token.LPAREN)
                self.expect(Token.RPAREN)
                return ExpGet()
            elif self.peek()['type'] == Token.LBRACK:
                indices = []
                while self.peek()['type'] == Token.LBRACK:
                    self.seek()
                    indices += [self.parse_expression()]
                    self.expect(Token.RBRACK)
                return ExpArrayElement(token['token'], indices)
            else:
                return ExpVariable(token['token'])
        elif self.peek()['type'] == Token.INT:
            value = self.peek()['val']
            self.seek()
            return ExpInteger(value)
        elif self.peek()['type'] == Token.LPAREN:
            self.seek()
            expr = self.parse_expression()
            self.expect(Token.RPAREN)
            return expr
        elif self.peek()['type'] == Token.LBRACE:
            return self.parse_block_expression()
        else:
            raise SyntaxError(f"Unexpected token: {self.peek()}.")


class Compiler:
    def __init__(self, string):
        lex = Lexer(string)
        lex.analyze()
        parser = Parser(lex)
        self.prog = parser.parse_program()

    def codegen(self, debug):
        sm = StackMachine()
        tables = []
        print(self.prog.string(0), file=sys.stderr)
        return self.prog.codegen(sm, tables, debug)


if __name__ == '__main__':
    import sys
    
    with open(sys.argv[1]) as f:
        prog = f.read()
    debug = True
    comp = Compiler(prog)
    code = comp.codegen(debug)
    if debug:
        print(code)
    else:
        for i in range(0, len(code), 80):
            print(code[i : i + 80])

