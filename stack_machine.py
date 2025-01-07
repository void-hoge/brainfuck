#!/usr/bin/env python3

import math


def sanitize(num):
    if num < 0:
        return f'neg{-num}'
    else:
        return f'{num}'


def mvp(num):
    '''move pointer'''
    if num < 0:
        return '<' * -num
    else:
        return '>' * num


def inc(num):
    '''increment'''
    if num < 0:
        return '-' * -num
    else:
        return '+' * num


def multi_dst_add(dsts):
    assert dsts
    assert 0 not in dsts
    data = sorted(set(dsts))
    ascending = [data[i + 1] - data[i] for i in range(len(data) - 1)]
    begin = data[0]
    code = ''
    code += f'[-{mvp(begin)}+'
    ret = begin
    for diff in ascending:
        ret += diff
        code += f'{mvp(diff)}+'
    code += f'{mvp(-ret)}]'
    return code


def multi_dst_subtract(dsts):
    '''Same as multi_dst_add but it subtract.'''
    assert dsts
    assert 0 not in dsts
    data = sorted(set(dsts))
    ascending = [data[i + 1] - data[i] for i in range(len(data) - 1)]
    begin = data[0]
    code = ''
    code += f'[-{mvp(begin)}-'
    ret = begin
    for diff in ascending:
        ret += diff
        code += f'{mvp(diff)}-'
    code += f'{mvp(-ret)}]'
    return code


def dimlength(shape, dim):
    def rec(shape, dim):
        if len(shape) - 1 == dim:
            return shape[dim] + 4
        else:
            return (rec(shape, dim + 1) + 1) * shape[dim]

    return rec(shape, dim + 1)


class StackMachine:
    def __init__(self):
        self.dp = 0
        self.controlstack = []

    def load_constant(self, value, debug=False):
        code = f'lc {sanitize(value)}: ' if debug else ''
        code += f'[-]{inc(value)}>'
        self.dp += 1
        return code + '\n' if debug else code

    def load_variable(self, pos, debug=False):
        assert 0 <= pos < self.dp
        rpos = pos - self.dp
        code = f'lv {pos}: ' if debug else ''
        code += '>[-]<'
        code += mvp(rpos)
        code += multi_dst_add([-rpos, -rpos + 1])
        code += mvp(-rpos + 1)
        code += multi_dst_add([rpos - 1])
        self.dp += 1
        return code + '\n' if debug else code

    def store_variable(self, pos, debug=False):
        assert 0 <= pos < self.dp
        self.dp -= 1
        code = f'sv {sanitize(pos)}: ' if debug else ''
        rpos = pos - self.dp
        code += mvp(rpos - 1)
        code += '[-]'
        code += mvp(-rpos)
        code += multi_dst_add([rpos])
        return code + '\n' if debug else code

    def add(self, debug=False):
        assert 1 < self.dp
        code = f'add: ' if debug else ''
        code += '<'
        code += multi_dst_add([-1])
        self.dp -= 1
        return code + '\n' if debug else code

    def subtract(self, debug=False):
        assert 1 < self.dp
        code = f'sub: ' if debug else ''
        code += '<'
        code += multi_dst_subtract([-1])
        self.dp -= 1
        return code + '\n' if debug else code

    def multiply(self, debug=False):
        assert 1 < self.dp
        code = 'mul: ' if debug else ''
        code += '[-]>[-]<<'
        code += '[-<'
        code += multi_dst_add([2, 3])
        code += '>>>'
        code += multi_dst_add([-3])
        code += '<<]'
        code += '<[-]>>'
        code += multi_dst_add([-2])
        code += '<'
        self.dp -= 1
        return code + '\n' if debug else code

    def boolean(self, debug=False):
        assert 0 < self.dp
        code = 'bool: ' if debug else ''
        code += '[-]<[[-]>+<]'
        code += '>'
        code += multi_dst_add([-1])
        return code + '\n' if debug else code

    def boolnot(self, debug=False):
        assert 0 < self.dp
        code = 'not: ' if debug else ''
        code += '[-]+<[[-]>-<]'
        code += '>'
        code += multi_dst_add([-1])
        return code + '\n' if debug else code

    def notequal(self, debug=False):
        assert 1 < self.dp
        code = 'neq: ' if debug else ''
        code += '<'
        code += multi_dst_subtract([-1])
        code += self.boolean()
        self.dp -= 1
        return code + '\n' if debug else code

    def equal(self, debug=False):
        assert 1 < self.dp
        code = 'eq: ' if debug else ''
        code += '<'
        code += multi_dst_subtract([-1])
        code += self.boolnot()
        self.dp -= 1
        return code + '\n' if debug else code

    def put_character(self, debug=False):
        assert 0 < self.dp
        code = 'putc: ' if debug else ''
        code += '<.[-]'
        self.dp -= 1
        return code + '\n' if debug else code

    def get_character(self, debug=False):
        code = 'getc: ' if debug else ''
        code += ',>'
        self.dp += 1
        return code + '\n' if debug else code

    def begin_while(self, debug=False):
        assert 0 < self.dp
        self.controlstack += [('while', self.dp)]
        code = 'beginwhile: ' if debug else ''
        code += '<[[-]'
        self.dp -= 1
        return code + '\n' if debug else code

    def end_while(self, debug=False):
        assert self.controlstack
        assert self.controlstack[-1][0] == 'while'
        assert self.controlstack[-1][1] == self.dp
        _, dp = self.controlstack.pop()
        code = 'endwhile: ' if debug else ''
        code += '<]'
        self.dp = dp - 1
        return code + '\n' if debug else code

    def greater_than(self, debug=False):
        assert 1 < self.dp
        self.dp -= 1
        code = 'gt: ' if debug else ''
        code += '[-]>[-]+>[-]+>[-]'
        code += '<'
        code += '[<<<<[>]>>>[->]<<<<-<->>>>]<[-]<<+[-]<+[[-]>+<]>[-<+>]'
        return code + '\n' if debug else code

    def less_than(self, debug=False):
        assert 1 < self.dp
        self.dp -= 1
        code = 'lt: ' if debug else ''
        code += '[-]>[-]+>[-]+>[-]'
        code += '<'
        code += '[<<<<[>]>>>[->]<<<<-<->>>>]<[-]<<+<+[-]>[[-]<+>]'
        return code + '\n' if debug else code

    def greater_or_equal(self, debug=False):
        assert 1 < self.dp
        code = 'ge: ' if debug else ''
        code += self.less_than()
        code += self.boolnot()
        return code + '\n' if debug else code

    def less_or_equal(self, debug=False):
        assert 1 < self.dp
        code = 'le: ' if debug else ''
        code += self.greater_than()
        code += self.boolnot()
        return code + '\n' if debug else code

    def modulo(self, debug=False):
        assert 1 < self.dp
        code = 'mod: ' if debug else ''
        code += '<<[->>+>+<<<]'
        code += '>>>[-<<<+>>>]'
        code += '<<[->>+>+<<<]'
        code += '>>>[-<<<+>>>]'
        self.dp += 1
        code += self.greater_or_equal()
        code += '<'
        code += '['
        code += '-<[-<->>+>+<<]'
        code += '>[-<+>]'
        code += '<<[->>+>>+<<<<]'
        code += '>>>>[-<<<<+>>>>]'
        self.dp += 1
        code += self.greater_or_equal()
        code += '<]'
        code += '<[-]'
        self.dp -= 1
        return code + '\n' if debug else code

    def divide(self, debug=False):
        assert 1 < self.dp
        code = 'div: ' if debug else ''
        code += '<<[->>>+>+<<<<]'
        code += '>>>>[-<<<<+>>>>]'
        code += '<<<[->>>+>+<<<<]'
        code += '>>>>[-<<<<+>>>>]'
        self.dp += 1
        code += self.greater_or_equal()
        code += '<'
        code += '['
        code += '-<+<[-<->>>+>+<<<]'
        code += '>>[-<<+>>]'
        code += '<<<[->>>+>>+<<<<<]'
        code += '>>>>>[-<<<<<+>>>>>]'
        self.dp += 1
        code += self.greater_or_equal()
        code += '<]'
        code += '<<[-]<[-]'
        code += '>>[-<<+>>]<'
        self.dp -= 1
        return code + '\n' if debug else code

    def begin_if(self, debug=False):
        assert 0 < self.dp
        self.controlstack += [('if', self.dp)]
        code = 'beginif: ' if debug else ''
        code += '+<[[-]>->'
        self.dp += 1
        return code + '\n' if debug else code

    def begin_else(self, debug=False):
        assert self.controlstack
        assert self.controlstack[-1][0] == 'if'
        assert self.controlstack[-1][1] == self.dp - 1
        _, dp = self.controlstack.pop()
        self.controlstack += [('else', dp)]
        code = 'beginelse: ' if debug else ''
        code += '[-]<' * (self.dp - dp + 1)
        code += ']>[->'
        self.dp = dp + 1
        return code + '\n' if debug else code

    def end_if(self, debug=False):
        assert self.controlstack
        assert self.controlstack[-1][0] == 'else'
        assert self.controlstack[-1][1] == self.dp - 1
        _, dp = self.controlstack.pop()
        code = 'endif: ' if debug else ''
        code += '[-]<' * (self.dp - dp)
        code += ']<'
        self.dp = dp - 1
        return code + '\n' if debug else code

    def load_address(self, pos, debug=False):
        '''pop and push data[pos - {top} - 1]'''
        assert 0 < self.dp
        assert 0 <= pos < self.dp
        rpos = pos - self.dp
        code = f'la {pos}: ' if debug else ''
        code += mvp(rpos)
        code += '[-]>[-]>[-]>[-]'
        code += mvp(-rpos - 4)
        code += multi_dst_add([rpos + 1])
        code += mvp(rpos + 1)
        code += '[<[->>>>+<<<<]>-[-<+>]>[-<+>]<+<]'
        code += '<[->+>>+<<<]>[-<+>]>'
        code += '[>[->+<]<-[->+<]>>>[-<<<<+>>>>]<<]'
        code += '>'
        code += multi_dst_add([-rpos - 3])
        code += mvp(-rpos - 2)
        return code + '\n' if debug else code

    def store_address(self, pos, debug=False):
        assert 1 < self.dp
        assert 0 <= pos < self.dp
        rpos = pos - self.dp
        code = f'sa {pos}: ' if debug else ''
        code += mvp(rpos)
        code += '[-]>[-]>[-]>[-]'
        code += mvp(-rpos - 5)
        code += multi_dst_add([rpos + 4])
        code += '>'
        code += multi_dst_add([rpos + 1])
        code += mvp(rpos + 1)
        code += '[-<[->>>>+<<<<]>[-<+>]>[-<+>]>[-<+>]<<+<]'
        code += '<[-]>>>[-<<<+>>>]<'
        code += '[->>>[-<<<<+>>>>]<<<[->+<]>]'
        code += mvp(-rpos - 3)
        self.dp -= 2
        return code + '\n' if debug else code

    def boolor(self, debug=False):
        assert 1 < self.dp
        code = 'or: ' if debug else ''
        code += '[-]>[-]<<<'
        code += '[[-]>>+<<]'
        code += '>[[-]>>+<<]'
        code += '>>[-<+>]'
        code += '<[[-]<<+>>]<'
        self.dp -= 1
        return code + '\n' if debug else code

    def booland(self, debug=False):
        assert 1 < self.dp
        code = 'and: ' if debug else ''
        code += '[-]+>[-]+<<<'
        code += '[[-]>>-<<]'
        code += '>[[-]>>-<<]'
        code += '>>[-<+>]'
        code += '<<<+'
        code += '>>[[-]<<->>]<'
        self.dp -= 1
        return code + '\n' if debug else code

    def pop(self, amount, debug=False):
        assert 0 < self.dp
        assert 0 <= amount
        code = f'pop {sanitize(amount)}: ' if debug else ''
        code += '<[-]' * amount
        self.dp -= amount
        return code + '\n' if debug else code

    def push_array(self, size, debug=False):
        code = 'initarr: ' if debug else ''
        code += mvp(size + 4)
        self.dp += size + 4
        return code + '\n' if debug else code

    def clean(self, begin, end, debug=False):
        assert 0 <= begin
        assert begin <= end
        assert end <= self.dp
        code = 'clean: ' if debug else ''
        code += mvp(begin - self.dp)
        code += '[-]>' * (end - begin)
        code += mvp(self.dp - end)
        return code + '\n' if debug else code

    def put_array(self, pos, debug=False):
        assert 0 <= pos
        assert pos <= self.dp
        code = 'puta: ' if debug else ''
        code += mvp(pos - self.dp)
        code += '<[.<]>[>]'
        code += mvp(self.dp - pos)
        return code + '\n' if debug else code

    def push_multi_dim_array(self, shape, debug=False):
        assert 0 <= self.dp
        assert len(shape) > 0
        assert 0 not in shape
        code = f'push multi dim array ({" ".join(map(str, shape))}): ' if debug else ''

        def initialize(shape, dim):
            nonlocal code
            if dim == len(shape) - 1:
                for i in range(shape[dim]):
                    code += self.load_constant(0, False)
                for _ in range(4):
                    code += self.load_constant(0, False)
            else:
                for i in range(shape[dim]):
                    initialize(shape, dim + 1)
            if dim != 0:
                code += self.load_constant(0, False)

        initialize(shape, 0)
        return code + '\n' if debug else code

    def multi_dim_load(self, pos, shape, debug=False):
        assert 0 < pos
        assert len(shape) < self.dp
        assert pos <= self.dp
        rpos = pos - self.dp
        code = f'mdl {pos} ({" ".join(map(str, shape))}): ' if debug else ''
        for s in shape:
            code += '<'
            code += multi_dst_add([rpos - 1])
        code += mvp(rpos + len(shape) - 2)
        for dim, size in enumerate(shape[:-1]):
            dimlen = dimlength(shape, dim) + 1
            code += '[>'
            for _ in range(len(shape) - dim + 1):
                code += multi_dst_add([-dimlen])
                code += '<'
            code += mvp(-dimlen + len(shape) - dim + 1) + '+'
            code += '<-]'
            code += '<'
        code += '[-<<<[->>>>+<<<<]>>[-<+>]<+>>[-<+>]<]<<<'
        code += '[->+>>+<<<]>[-<+>]>'
        code += '[->>>[-<<<<+>>>>]<<[->+<]<[->+<]>]>>>'
        for dim, size in enumerate(shape[:-1]):
            dimlen = dimlength(shape, len(shape) - dim - 2) + 1
            code += '[-'
            code += multi_dst_add([dimlen])
            code += mvp(-dim - 2)
            code += multi_dst_add([dimlen])
            code += mvp(dimlen + dim + 2)
            code += ']'
            code += '>'
        code += mvp(-len(shape) - 1)
        code += multi_dst_add([-rpos + 1])
        code += mvp(-rpos + 2)
        self.dp -= len(shape) - 1
        return code + '\n' if debug else code

    def multi_dim_store(self, pos, shape, debug=False):
        assert 0 < pos
        assert len(shape) < self.dp
        assert pos <= self.dp
        rpos = pos - self.dp
        code = f'mds {pos} ({" ".join(map(str, shape))}): ' if debug else ''
        for s in shape:
            code += '<'
            code += multi_dst_add([rpos - 1])
        code += '<'
        code += multi_dst_add([rpos - 1])
        code += mvp(rpos + len(shape) - 1)
        for dim, size in enumerate(shape[:-1]):
            dimlen = dimlength(shape, dim) + 1
            code += '[>'
            for _ in range(len(shape) - dim + 2):
                code += multi_dst_add([-dimlen])
                code += '<'
            code += mvp(-dimlen + len(shape) - dim + 2) + '+'
            code += '<-]'
            code += '<'
        code += '[<<<[->>>>+<<<<]>[-<+>]<+>>[-<+>]>-[-<+>]<]'
        code += '<<<[-]>>[-<<+>>]<[->+<]>'
        code += '[->>>[-<<<<+>>>>]<<<[->+<]>]>>>'
        for dim, size in enumerate(shape[:-1]):
            dimlen = dimlength(shape, len(shape) - dim - 2) + 1
            code += '[-'
            code += multi_dst_add([dimlen])
            code += mvp(dimlen)
            code += ']>'
        code += mvp(-len(shape) - rpos - 1)
        self.dp -= len(shape) + 1
        return code + '\n' if debug else code

    def multi_dim_put(self, pos, shape, debug=False):
        assert 0 < pos
        assert len(shape) - 1 < self.dp
        assert pos <= self.dp
        rpos = pos - self.dp
        code = f'mdp {pos} ({" ".join(map(str, shape))}): ' if debug else ''
        for s in shape[:-1]:
            code += '<'
            code += multi_dst_add([rpos - 1])
        code += mvp(rpos + len(shape) - 3)
        for dim, size in enumerate(shape[:-1]):
            dimlen = dimlength(shape, dim) + 1
            code += '[>'
            for _ in range(len(shape) - dim + 2):
                code += multi_dst_add([-dimlen])
                code += '<'
            code += mvp(-dimlen + len(shape) - dim + 2) + '+'
            code += '<-]'
            code += '<'
        code += '<<<'
        code += '[.<]>[>]>>>>'
        for dim, size in enumerate(shape[:-1]):
            dimlen = dimlength(shape, len(shape) - dim - 2) + 1
            code += '[-'
            code += multi_dst_add([dimlen])
            code += mvp(dimlen)
            code += ']>'
        code += mvp(-rpos - len(shape) + 1)
        self.dp -= len(shape) - 1
        return code + '\n' if debug else code

    def load_hex(self, length, num, debug=False):
        assert 0 <= num
        assert 0 < length
        code = f'loadhex {length} {num}: ' if debug else ''
        for i in range(length)[::-1]:
            code += self.load_constant(num // (16 ** i))
            num %= 16 ** i
        return code + '\n' if debug else code

    def add_hex(self, length, debug=False):
        assert 0 < length
        assert length * 2 <= self.dp
        code = f'addhex {length}: ' if debug else ''
        code += '[-]'
        for i in range(length):
            code += '[-<+>]'
            code += mvp(-length - 1)
            code += multi_dst_add([length])
            code += mvp(length)
            code += '[->+>+<<]>>[-<<+>>]'
            code += inc(16)
            code += '>'
            code += self.greater_or_equal()
            code += f'<[[-]>+<<{inc(-16)}>]<'
            code += multi_dst_add([-length])
            code += '>>[-<<+>>]<<'
        code += '[-]'
        return code + '\n' if debug else code

    def inv_hex(self, length, debug=False):
        assert 0 < length
        assert length <= self.dp
        code = f'invhex {length}: ' if debug else ''
        for i in range(length):
            code += f'{inc(15)}'
            code += mvp(-i - 1)
            code += multi_dst_subtract([i + 1])
            code += mvp(i + 1)
            code += multi_dst_add([-i - 1])
        code += self.load_hex(length, 1)
        code += self.add_hex(length)
        return code + '\n' if debug else code

    def subtract_hex(self, length, debug=False):
        assert 0 < length
        assert length * 2 <= self.dp
        code = f'subhex {length}: ' if debug else ''
        code += self.inv_hex(length)
        code += self.add_hex(length)
        return code + '\n' if debug else code
