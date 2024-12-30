#!/usr/bin/env python3

import sys
from enum import IntEnum, auto
from lexer import Token, LexicalAnalyzer
from stack_machine import *

STKBYTES = 2


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

    def __str__(self):
        return self.string(0)

    def codegen(self, debug):
        tables = [{}]
        code = ''
        sm = StackMachine()
        for st in self.statements:
            if isinstance(st, StInitVariable) or isinstance(st, StInitArray):
                code += st.allocate(sm, self.funcs, tables, debug)
            else:
                code += st.codegen(sm, self.funcs, tables, debug)
        if debug:
            return code
        else:
            prog = ''
            for i in range(0, len(code), 80):
                prog += code[i : i + 80] + '\n'
            return prog


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

    def store_frame(self, sm, size, debug):
        code = f'store stack {size}\n'
        for _ in range(size):
            for i in range(STKBYTES)[::-1]:
                code += sm.load_variable(self.frameptr_pos + i, debug)
            code += sm.multi_dim_store(self.frame_pos, self.frame_shape, debug)
            for i in range(STKBYTES):
                code += sm.load_variable(self.frameptr_pos + i, debug)
            code += sm.load_hex(STKBYTES, 1, debug)
            code += sm.add_hex(STKBYTES, debug)
            for i in range(STKBYTES)[::-1]:
                code += sm.store_variable(self.frameptr_pos + i, debug)
        return code

    def restore_frame(self, sm, size, debug):
        code = f'restore stack {size}\n'
        for _ in range(size):
            for i in range(STKBYTES):
                code += sm.load_variable(self.frameptr_pos + i, debug)
            code += sm.load_hex(STKBYTES, 1, debug)
            code += sm.subtract_hex(STKBYTES, debug)
            for i in range(STKBYTES)[::-1]:
                code += sm.store_variable(self.frameptr_pos + i, debug)
            for i in range(STKBYTES)[::-1]:
                code += sm.load_variable(self.frameptr_pos + i, debug)
            code += sm.multi_dim_load(self.frame_pos, self.frame_shape, debug)
        return code

    def store_args(self, sm, size, debug):
        code = f'store arguments {size}\n'
        for _ in range(size):
            code += sm.load_variable(self.argbuffptr_pos, debug)
            code += sm.multi_dim_store(self.argbuff_pos, [self.max_arglen], debug)
            code += sm.load_variable(self.argbuffptr_pos, debug)
            code += sm.load_constant(1, debug)
            code += sm.add(debug)
            code += sm.store_variable(self.argbuffptr_pos, debug)
        return code

    def restore_args(self, sm, size, debug):
        code = f'restore arguments {size}\n'
        for _ in range(size):
            code += sm.load_variable(self.argbuffptr_pos, debug)
            code += sm.load_constant(1, debug)
            code += sm.subtract(debug)
            code += sm.store_variable(self.argbuffptr_pos, debug)
            code += sm.load_variable(self.argbuffptr_pos, debug)
            code += sm.multi_dim_load(self.argbuff_pos, [self.max_arglen], debug)
        return code

    def set_state(self, sm, state, debug):
        state = [int(ch) for ch in f'{state:0{self.num_states.bit_length()}b}']
        code = 'set state\n'
        for i, num in enumerate(state):
            code += sm.load_constant(num, debug)
            code += sm.store_variable(self.state_pos + i, debug)
        return code

    def init_callenv(self, sm, funcs, debug):
        calls = []
        self.extract_calls(0, calls)
        self.funcset = {call['name'] for call in calls} | {self.name}
        self.num_states = 0
        self.func_table = {}
        for name in self.funcset:
            self.func_table[name] = self.num_states
            self.num_states += funcs[name].count_states(1)
        self.max_arglen = max(1, max(len(funcs[name].args) for name in self.funcset))
        code = ''
        # allocate return
        code += 'return pos\n'
        self.return_pos = sm.dp
        code += sm.load_constant(0, debug)
        # allocate frame stack
        code += 'frame stack\n'
        self.frame_shape = [16] * STKBYTES
        code += sm.push_multi_dim_array(self.frame_shape, debug)
        self.frame_pos = sm.dp
        # allocate frame stack pointer (big-endian, right is lower)
        code += 'frame stack pointer\n'
        self.frameptr_pos = sm.dp
        for _ in range(STKBYTES):
            code += sm.load_constant(0, debug)
        # allocate argument buffer
        code += 'argument buffer\n'
        code += sm.push_multi_dim_array([self.max_arglen], debug)
        self.argbuff_pos = sm.dp
        code += 'argument buffer pointer\n'
        self.argbuffptr_pos = sm.dp
        code += sm.load_constant(0, debug)
        # allocate state variable
        code += 'state variable\n'
        self.state_pos = sm.dp
        for _ in range(self.num_states.bit_length()):
            code += sm.load_constant(0, debug)
        return code

    def codegen(self, sm, funcs, tables, args, debug):
        if len(args) != len(self.args):
            raise SyntaxError(
                f'The function {repr(self.name)} must take just {len(self.args)} arguments, but entered {len(args)}.'
            )
        code = self.init_callenv(sm, funcs, debug)
        # load arguments
        code += 'load arguments\n'
        for arg, argv in zip(self.args, args):
            code += StInitVariable(arg.name, argv).allocate(sm, funcs, tables + [{}], debug)
        code += self.store_args(sm, len(args), debug)

        # mainloop
        code += 'mainloop\n'
        code += sm.load_constant(1, debug)
        code += sm.begin_while(debug)

        for _ in range(self.num_states.bit_length()):
            sm.load_constant(0, debug)
            sm.load_constant(0, debug)
        self.base = sm.dp
        blocks = [[]]
        self.blockgen(sm, funcs, tables, blocks, self, debug)
        sm.pop(self.num_states.bit_length() * 2, debug)

        def rec(blkidx):
            code = ''
            if len(blkidx) == self.num_states.bit_length():
                idx = sum(num << place for place, num in enumerate(blkidx))
                if idx < len(blocks):
                    for line in blocks[idx]:
                        code += line
            else:
                code += sm.load_variable(self.state_pos + len(blkidx), debug)
                code += sm.begin_if(debug)
                code += rec(blkidx + [1])
                code += sm.begin_else(debug)
                code += rec(blkidx + [0])
                code += sm.end_if(debug)
            return code

        code += rec([])

        # check condition
        code += 'condition\n'
        finish = [int(ch) for ch in f'{self.num_states:b}']
        for i, num in enumerate(finish):
            code += sm.load_variable(self.state_pos + i, debug)
            code += sm.load_constant(num, debug)
            code += sm.notequal(debug)
        for _ in range(self.num_states.bit_length() - 1):
            code += sm.boolor(debug)
        code += sm.end_while(debug)
        # return
        for _ in range(STKBYTES):
            code += sm.load_constant(0, debug)
        code += sm.multi_dim_load(self.frame_pos, self.frame_shape, debug)
        code += sm.store_variable(self.return_pos, debug)
        # clean
        code += sm.pop(sm.dp - self.return_pos - 1, debug)
        return code

    def extract_calls(self, index, calls):
        for st in self.body:
            index = st.extract_calls(index, calls)
        return index

    def count_states(self, index):
        for st in self.body:
            index = st.count_states(index)
            if isinstance(st, StReturn):
                break
        return index

    def blockgen(self, sm, funcs, tables, blocks, func, debug):
        lvars = {}
        for i, arg in enumerate(func.args):
            assert arg.name not in lvars
            lvars[arg.name] = {'type': 'variable', 'pos': sm.dp + i, 'size': 1}
        blocks[-1] += [func.restore_args(sm, len(func.args), debug)]
        for st in self.body:
            st.blockgen(sm, funcs, tables + [lvars], blocks, func, debug)


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
            Token.ASSIGN: lambda _: '',
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

    def extract_calls(self, index, calls):
        return self.rhs.extract_calls(index, calls)

    def needs_expansion(self):
        return self.rhs.needs_expansion()

    def count_states(self, index):
        return self.rhs.count_states(index)


class StReturn(Statement):
    def __init__(self, expr):
        self.expr = expr

    def string(self, level):
        return f'{indent(level)}return {self.expr};'

    def extract_calls(self, index, calls):
        return self.expr.extract_calls(index, calls)

    def needs_expansion(self):
        return True

    def count_states(self, index):
        return self.expr.count_states(index)

    def blockgen(self, sm, funcs, tables, blocks, func, debug):
        blocks[-1] += ['return\n']
        if self.expr.needs_expansion():
            self.expr.blockgen(sm, funcs, tables, blocks, func, debug)
        else:
            blocks[-1] += [self.expr.codegen(sm, funcs, tables, debug)]
        blocks[-1] += [func.store_args(sm, 1, debug)]
        blocks[-1] += [sm.pop(sm.dp - func.base, debug)]
        for i in range(STKBYTES):
            blocks[-1] += [sm.load_variable(func.state_pos + i, debug)]
            blocks[-1] += [sm.load_constant(0, debug)]
            blocks[-1] += [sm.equal(debug)]
        for _ in range(STKBYTES - 1):
            blocks[-1] += [sm.booland(debug)]
        blocks[-1] += [sm.begin_if(debug)]
        blocks[-1] += [func.set_state(sm, func.num_states, debug)]
        blocks[-1] += [sm.begin_else(debug)]
        blocks[-1] += [func.restore_frame(sm, STKBYTES, debug)]
        for i in range(STKBYTES)[::-1]:
            blocks[-1] += [sm.store_variable(func.state_pos + i, debug)]
        blocks[-1] += [sm.end_if(debug)]


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

    def extract_calls(self, index, calls):
        index = self.cond.extract_calls(index, calls)
        for st in self.body:
            index = st.extract_calls(index, calls)
        return index

    def needs_expansion(self):
        if self.cond.needs_expansion():
            return True
        for st in self.body:
            if st.needs_expansion():
                return True
        return False

    def count_states(self, index):
        if self.needs_expansion():
            index += 1
            index = self.cond.count_states(index)
            for st in self.body:
                index = st.count_states(index)
                if isinstance(st, StReturn):
                    break
            return index + 1
        else:
            return index


class StIf(Statement):
    def __init__(self, cond, body_then, body_else=[]):
        self.cond = cond
        self.body_then = body_then
        self.body_else = body_else

    def string(self, level):
        code = f'{indent(level)}if ({self.cond}) {{\n'
        for st in self.body_then:
            code += st.string(level + 1) + '\n'
        code += f'{indent(level)}}}'
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
        for st in self.body_else:
            if isinstance(st, StInitVariable) or isinstance(st, StInitArray):
                code += st.allocate(sm, funcs, tables + [lvars], debug)
        size = sm.dp - base
        code += self.cond.codegen(sm, funcs, tables + [lvars], debug)
        code += sm.begin_if(debug)
        for st in self.body_then:
            code += st.codegen(sm, funcs, tables + [lvars], debug)
        code += sm.begin_else(debug)
        for st in self.body_else:
            code += st.codegen(sm, funcs, tables + [lvars], debug)
        code += sm.end_if(debug)
        code += sm.pop(size, debug)
        return code

    def extract_calls(self, index, calls):
        index = self.cond.extract_calls(index, calls)
        for st in self.body_then:
            index = st.extract_calls(index, calls)
        return index

    def needs_expansion(self):
        if self.cond.needs_expansion():
            return True
        for st in self.body_then:
            if st.needs_expansion():
                return True
        return False

    def count_states(self, index):
        if self.needs_expansion():
            index = self.cond.count_states(index)
            for st in self.body_then:
                index = st.count_states(index)
                if isinstance(st, StReturn):
                    break
            index += 1
            for st in self.body_else:
                index = st.count_states(index)
                if isinstance(st, StReturn):
                    break
            return index
        else:
            return index

    def blockgen(self, sm, funcs, tables, blocks, func, debug):
        blocks[-1] += ['if\n']
        if self.needs_expansion():
            blocks[-1] += [self.cond.codegen(sm, funcs, tables, debug)]
            blocks[-1] += [sm.begin_if(debug)]
            blocks[-1] += [func.set_state(len(blocks), sm, debug)]
            blocks[-1] += [sm.begin_else(debug)]
            gotoelse = len(blocks) - 1, len(blocks[-1])
            blocks[-1] += ['dummy']
            blocks[-1] += [sm.end_if(debug)]
            basesize = sm.dp - func.base
            for _ in range(basesize):
                blocks[-1] += [func.push_frame_stack(sm, debug)]

            # then
            blocks += [[]]
            for _ in range(basesize):
                blocks[-1] += [func.pop_frame_stack(sm, debug)]
            lvars = {}
            for st in self.body_then + self.body_else:
                if isinstance(st, StInitVariable) or isinstance(st, StInitArray):
                    blocks[-1] += [st.allocate(sm, funcs, tables + [lvars], debug)]
            size = sum(var['size'] for var in lvars.items())
            for st in self.body_then:
                st.blockgen(sm, funcs, tables, blocks, func, debug)
            gotobase = len(blocks) - 1, len(blocks[-1])
            blocks[-1] += ['dummy']
            blocks[-1] += [sm.pop(size, debug)]
            for _ in range(basesize):
                blocks[-1] += [func.push_frame_stack(sm, debug)]

            # else
            blocks += [[]]
            for _ in range(basesize):
                blocks[-1] += [func.pop_frame_stack(sm, debug)]
            lvars = {}
            for st in self.body_then + self.body_else:
                if isinstance(st, StInitVariable) or isinstance(st, StInitArray):
                    blocks[-1] += [st.allocate(sm, funcs, tables + [lvars], debug)]
            size = sum(var['size'] for var in lvars.items())
            for st in self.body_else:
                st.blockgen(sm, funcs, tables, blocks, func, debug)
            blocks[-1] += [func.set_state(len(blocks), sm, debug)]
            blocks[-1] += [sm.pop(size, debug)]
            for _ in range(basesize):
                blocks[-1] += [func.push_frame_stack(sm, debug)]

            blk, idx = gotoelse
            blocks[blk][idx] = [func.set_state(len(blocks) - 1, sm, debug)]

            # base
            blocks += [[]]
            for _ in range(basesize):
                blocks[-1] += [func.pop_frame_stack(sm, debug)]

            blk, idx = gotobase
            blocks[blk][idx] = [func.set_state(len(blocks) - 1, sm, debug)]
        else:
            blocks[-1] += self.codegen(sm, funcs, tables, debug)


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

    def extract_calls(self, index, calls):
        for init in self.inits:
            index = init.extract_calls(index, calls)
        index = self.cond.extract_calls(index, calls)
        for st in self.body:
            index = st.extract_calls(index, calls)
        for init in self.reinits:
            index = st.extract_calls(index, calls)
        return index

    def needs_expansion(self):
        for init in self.inits:
            if init.needs_expansion():
                return True
        if self.cond.needs_expansion():
            return True
        for st in self.body:
            if st.needs_expansion():
                return True
        for init in self.reinits:
            if init.needs_expansion():
                return True

    def count_states(self, index):
        if self.needs_expansion():
            for init in self.inits:
                index = init.count_states(index)
            index += 1
            index = self.cond.count_states(index)
            for st in self.body:
                index = st.count_states(index)
                if isinstance(st, StReturn):
                    break
            for init in self.reinits:
                index = init.count_states(index)
            return index + 1
        else:
            return index


class StCall(Statement):
    def __init__(self, expr):
        self.expr = expr

    def string(self, level):
        return f'{indent(level)}{self.expr};'

    def builtin_putchar(self, sm, debug):
        return sm.put_character(debug)

    def builtin_putint(self, sm, debug):
        code = ''
        pos = sm.dp - 1
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
        if self.expr.name in ['putchar', 'putint']:
            if len(self.expr.args) != 1:
                raise SyntaxError(f'Number of arguments of the built-in putchar and putint is 1.')
            code = self.expr.args[0].codegen(sm, funcs, tables, debug)
            if self.expr.name == 'putchar':
                return code + self.builtin_putchar(sm, debug)
            else:
                return code + self.builtin_putint(sm, debug)
        else:
            base = sm.dp
            code = self.expr.codegen(sm, funcs, tables, debug)
            code += sm.pop(sm.dp - base, debug)
            return code

    def extract_calls(self, index, calls):
        return self.expr.extract_calls(index, calls)

    def needs_expansion(self):
        if self.expr.name in ['putchar', 'putint']:
            if self.expr.args[0].needs_expansion():
                return True
            else:
                return False
        return self.expr.needs_expansion()

    def count_states(self, index):
        return self.expr.count_states(index)

    def blockgen(self, sm, funcs, tables, blocks, func, debug):
        if self.expr.name in ['putchar', 'putint']:
            if self.expr.args[0].needs_expansion():
                self.expr.blockgen(sm, funcs, tables, blocks, func, debug)
            else:
                blocks[-1] += [self.expr.args[0].codegen(sm, funcs, tables, debug)]
            if self.expr.name == 'putchar':
                blocks[-1] += [self.builtin_putchar(sm, debug)]
            else:
                blocks[-1] += [self.builtin_putint(sm, debug)]
        else:
            base = sm.dp
            self.expr.blockgen(sm, funcs, tables, blocks, func, debug)
            blocks[-1] += [sm.pop(sm.dp - base, debug)]


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

    def extract_calls(self, index, calls):
        if self.rhs:
            return self.rhs.extract_calls(index, calls)
        else:
            return index

    def needs_expansion(self):
        if self.rhs:
            if self.rhs.needs_expansion():
                return True
        return False

    def count_states(self, index):
        if self.rhs:
            return self.rhs.count_states(index)
        else:
            return index


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

    def extract_calls(self, index, calls):
        return index

    def needs_expansion(self):
        return False

    def count_states(self, index):
        return index


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
            if self.name in funcs:
                return funcs[self.name].codegen(sm, funcs, tables, self.args, debug)
            else:
                raise SyntaxError(f'Undefined function named {self.name}.')

    def extract_calls(self, index, calls):
        for arg in self.args:
            index = arg.extract_calls(index, calls)
        if self.name not in ['putchar', 'putint', 'getchar', 'getint']:
            self.index = index
            calls += [{'name': self.name, 'index': index}]
        return index + 1

    def needs_expansion(self):
        if any(arg.needs_expansion() for arg in self.args):
            return True
        if self.name in ['putchar', 'putint', 'getchar', 'getint']:
            return False
        return True

    def count_states(self, index):
        for arg in self.args:
            index = arg.count_states(index)
        if self.name in ['putchar', 'putint', 'getchar', 'getint']:
            return index
        else:
            return index + 1

    def blockgen(self, sm, funcs, tables, blocks, func, debug):
        if self.name == 'getchar':
            blocks[-1] += [self.builtin_getchar(sm, funcs, tables, debug)]
        elif self.name == 'getint':
            blocks[-1] += [self.builtin_getint(sm, funcs, tables, debug)]
        else:
            raise NotImplementedError


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

    def extract_calls(self, index, calls):
        for idx in self.indices:
            index = idx.extract_calls(index, calls)
        return index

    def needs_expansion(self):
        for idx in self.indices:
            if idx.needs_expansion():
                return True
        return False

    def count_states(self, index):
        for idx in self.indices:
            index = idx.count_states(index)
        return index


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

    def extract_calls(self, index, calls):
        return index

    def needs_expansion(self):
        return False

    def count_states(self, index):
        return index


class ExpInteger(Expression):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

    def evaluate(self):
        return self.value

    def codegen(self, sm, funcs, tables, debug):
        return sm.load_constant(self.value, debug)

    def extract_calls(self, index, calls):
        return index

    def needs_expansion(self):
        return False

    def count_states(self, index):
        return index

    def blockgen(self, sm, funcs, tables, blocks, func, debug):
        blocks[-1] += [self.codegen(sm, funcs, tables, debug)]


class ExpCharacter(Expression):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

    def evaluate(self):
        return self.value

    def codegen(self, sm, funcs, tables, debug):
        return sm.load_constant(self.value, debug)

    def extract_calls(self, index, calls):
        return index

    def needs_expansion(self):
        return False

    def count_states(self, index):
        return index

    def blockgen(self, sm, funcs, tables, blocks, func, debug):
        blocks[-1] += [self.codegen(sm, funcs, tables, debug)]


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

    def extract_calls(self, index, calls):
        index = self.left.extract_calls(index, calls)
        index = self.right.extract_calls(index, calls)
        return index

    def needs_expansion(self):
        return self.left.needs_expansion() or self.right.needs_expansion()

    def count_states(self, index):
        index = self.left.count_states(index)
        return self.right.count_states(index)


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

    def extract_calls(self, index, calls):
        index = self.left.extract_calls(index, calls)
        index = self.right.extract_calls(index, calls)
        return index

    def needs_expansion(self):
        return self.left.needs_expansion() or self.right.needs_expansion()

    def count_states(self, index):
        index = self.left.count_states(index)
        return self.right.count_states(index)


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

    def extract_calls(self, index, calls):
        index = self.left.extract_calls(index, calls)
        index = self.right.extract_calls(index, calls)
        return index

    def needs_expansion(self):
        return self.left.needs_expansion() or self.right.needs_expansion()

    def count_states(self, index):
        index = self.left.count_states(index)
        return self.right.count_states(index)


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
        else:  # self.mode == Token.GE:
            return code + sm.greater_or_equal(debug)

    def extract_calls(self, index, calls):
        index = self.left.extract_calls(index, calls)
        index = self.right.extract_calls(index, calls)
        return index

    def needs_expansion(self):
        return self.left.needs_expansion() or self.right.needs_expansion()

    def count_states(self, index):
        index = self.left.count_states(index)
        return self.right.count_states(index)


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
        else:  # self.mode == Token.MINUS
            return code + sm.subtract(debug)

    def extract_calls(self, index, calls):
        index = self.left.extract_calls(index, calls)
        index = self.right.extract_calls(index, calls)
        return index

    def needs_expansion(self):
        return self.left.needs_expansion() or self.right.needs_expansion()

    def count_states(self, index):
        index = self.left.count_states(index)
        return self.right.count_states(index)


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
        else:  # self.mode == Token.PERCENT
            return code + sm.modulo(debug)

    def extract_calls(self, index, calls):
        index = self.left.extract_calls(index, calls)
        index = self.right.extract_calls(index, calls)
        return index

    def needs_expansion(self):
        return self.left.needs_expansion() or self.right.needs_expansion()

    def count_states(self, index):
        index = self.left.count_states(index)
        return self.right.count_states(index)


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

    def extract_calls(self, index, calls):
        return self.operand.extract_calls(index, calls)

    def needs_expansion(self):
        return self.operand.needs_expansion()

    def count_states(self, index):
        return self.operand.count_states(index)


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
            raise SyntaxError(
                f'Expected {repr(Token.ID)}, got {repr(self.peek()["type"])} in line {token["line"] + 1}.'
            )
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
                raise SyntaxError(
                    f'Unexpected token {repr(Token.KW_VAR)} or {repr(Token.KW_ARR)}, got {repr(self.peek()["type"])} in line {self.peek()["line"] + 1}.'
                )
            self.match(Token.COMMA)
        self.expect(Token.RPAREN)
        self.expect(Token.LBRACE)
        body = []
        while self.peek()['type'] != Token.RBRACE:
            body += [self.parse_statement(tables + [lvars], True)]
        if not body or not isinstance(body[-1], StReturn):
            body += [StReturn(ExpInteger(0))]
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
                raise SyntaxError(
                    f'Expected {repr(Token.KW_VAR)} or {repr(Token.ARR)}, got {repr(self.peek()["type"])} in line {self.peek()["line"] + 1}.'
                )
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
            tables[-1][name] = {'type': 'array', 'shape': [dim.evaluate() for dim in shape]}
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
                    raise SyntaxError(
                        f'The left-hand-side of the assign must be a reference of a single byte, in line {token["line"] + 1}.'
                    )
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
            raise SyntaxError(
                f'Expected {repr(Token.ID)}, got {repr(self.peek()["type"])} in line {token["line"] + 1}.'
            )
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
