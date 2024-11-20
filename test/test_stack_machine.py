#!/usr/bin/env pyton3

import unittest
from stack_machine import *
from interpreter import *
import io
import math

TESTALL = False


def run(code, input_string='', dump=False):
    ist = io.StringIO(input_string)
    ost = io.StringIO()
    print()
    print(code)
    dp, data, step = interpreter(code, ist, ost, dump)
    print(f'Halted after {step} steps of execution.')
    print(f'data: {data}')
    print(f'dp  : {dp}')
    print(f'out : {repr(ost.getvalue())}')
    return ost.getvalue(), dp, data


class TestStackMachine(unittest.TestCase):
    def test_000_move_value1(self):
        code = 'move value1\n'
        code += '+++++\n'
        code += multi_dst_add([1])
        out, dp, data = run(code)
        self.assertEqual([0, 5], data)

    def test_001_move_value2(self):
        code = 'move value2\n'
        code += '+++++\n'
        code += multi_dst_add([2])
        out, dp, data = run(code)
        self.assertEqual([0, 0, 5], data)

    def test_002_move_value3(self):
        code = 'move value3\n'
        code += '+++++\n'
        code += multi_dst_add([1, 2])
        out, dp, data = run(code)
        self.assertEqual([0, 5, 5], data)

    def test_003_sm_load_constant(self):
        sm = StackMachine()
        code = 'sm lc\n'
        code += sm.load_constant(ord('@'))
        out, dp, data = run(code)
        self.assertEqual([ord('@'), 0], data)
        self.assertEqual(1, dp)

    def test_004_sm_load_variable1(self):
        sm = StackMachine()
        code = 'sm lv\n'
        code += sm.load_constant(ord('a'))
        code += sm.load_variable(0)
        out, dp, data = run(code)
        self.assertEqual([ord('a'), ord('a'), 0], data)
        self.assertEqual(2, dp)

    def test_005_sm_store_variable1(self):
        sm = StackMachine()
        code = 'sm sv1\n'
        code += sm.load_constant(ord('a'))
        code += sm.load_variable(0)
        code += sm.store_variable(0)
        out, dp, data = run(code)
        self.assertEqual([ord('a'), 0, 0], data)
        self.assertEqual(1, dp)

    def test_006_sm_store_variable2(self):
        sm = StackMachine()
        code = 'sm sv2\n'
        code += sm.load_constant(ord('a'))
        code += sm.load_constant(ord('b'))
        code += sm.load_constant(ord('c'))
        code += sm.store_variable(0)
        out, dp, data = run(code)
        self.assertEqual([ord('c'), ord('b'), 0, 0], data)
        self.assertEqual(2, dp)

    def test_007_sm_add1(self):
        sm = StackMachine()
        code = 'sm add1\n'
        code += sm.load_constant(5)
        code += sm.load_constant(6)
        code += sm.add()
        out, dp, data = run(code)
        self.assertEqual([11, 0, 0], data)
        self.assertEqual(1, dp)

    def test_008_sm_sub1(self):
        sm = StackMachine()
        code = 'sm sub1\n'
        code += sm.load_constant(5)
        code += sm.load_constant(6)
        code += sm.subtract()
        out, dp, data = run(code)
        self.assertEqual([255, 0, 0], data)
        self.assertEqual(1, dp)

    def test_009_sm_mul1(self):
        sm = StackMachine()
        code = 'sm mul1\n'
        code += sm.load_constant(5)
        code += sm.load_constant(51)
        code += sm.multiply()
        out, dp, data = run(code)
        self.assertEqual([255, 0, 0, 0], data)
        self.assertEqual(1, dp)

    def test_010_sm_add_sub_all(self):
        if TESTALL:
            for x in range(256):
                for y in range(256):
                    sm = StackMachine()
                    code = f'sm add sub all {x} {y}\n'
                    code += sm.load_constant(x)
                    code += sm.load_constant(y)
                    code += sm.add()
                    code += sm.load_constant(x)
                    code += sm.load_constant(y)
                    code += sm.subtract()
                    out, dp, data = run(code)
                    self.assertEqual([(x + y) % 256, (x - y) % 256, 0, 0], data)
                    self.assertEqual(2, dp)

    def test_011_sm_bool1(self):
        sm = StackMachine()
        code = 'sm bool1\n'
        code += sm.load_constant(10)
        code += sm.boolean()
        out, dp, data = run(code)
        self.assertEqual([1, 0], data)
        self.assertEqual(1, dp)

    def test_012_sm_bool2(self):
        sm = StackMachine()
        code = 'sm bool2\n'
        code += sm.load_constant(0)
        code += sm.boolean()
        out, dp, data = run(code)
        self.assertEqual([0, 0], data)
        self.assertEqual(1, dp)

    def test_013_sm_boolnot1(self):
        sm = StackMachine()
        code = 'sm not1\n'
        code += sm.load_constant(0)
        code += sm.boolnot()
        out, dp, data = run(code)
        self.assertEqual([1, 0], data)
        self.assertEqual(1, dp)

    def test_014_sm_boolnot2(self):
        sm = StackMachine()
        code = 'sm not2\n'
        code += sm.load_constant(10)
        code += sm.boolnot()
        out, dp, data = run(code)
        self.assertEqual([0, 0], data)
        self.assertEqual(1, dp)

    def test_015_sm_bool_boolnot_all(self):
        if TESTALL:
            for x in range(256):
                sm = StackMachine()
                code = f'sm bool boolnot all {x}\n'
                code += sm.load_constant(x)
                code += sm.boolean()
                code += sm.load_constant(x)
                code += sm.boolnot()
                out, dp, data = run(code)
                self.assertEqual([int(bool(x)), int(not bool(x)), 0], data)
                self.assertEqual(2, dp)

    def test_016_sm_equal1(self):
        sm = StackMachine()
        code = 'sm equal1\n'
        code += sm.load_constant(10)
        code += sm.load_constant(10)
        code += sm.equal()
        out, dp, data = run(code)
        self.assertEqual([1, 0, 0], data)
        self.assertEqual(1, dp)

    def test_017_sm_equal2(self):
        sm = StackMachine()
        code = 'sm equal2\n'
        code += sm.load_constant(10)
        code += sm.load_constant(5)
        code += sm.equal()
        out, dp, data = run(code)
        self.assertEqual([0, 0, 0], data)
        self.assertEqual(1, dp)

    def test_018_sm_not_equal1(self):
        sm = StackMachine()
        code = 'sm neq1\n'
        code += sm.load_constant(10)
        code += sm.load_constant(10)
        code += sm.notequal()
        out, dp, data = run(code)
        self.assertEqual([0, 0, 0], data)
        self.assertEqual(1, dp)

    def test_019_sm_not_equal2(self):
        sm = StackMachine()
        code = 'sm neq2\n'
        code += sm.load_constant(10)
        code += sm.load_constant(5)
        code += sm.notequal()
        out, dp, data = run(code)
        self.assertEqual([1, 0, 0], data)
        self.assertEqual(1, dp)

    def test_020_sm_equal_notequal(self):
        if TESTALL:
            for x in range(256):
                for y in range(256):
                    sm = StackMachine()
                    code = f'sm eq neq all {x} {y}\n'
                    code += sm.load_constant(x)
                    code += sm.load_constant(y)
                    code += sm.equal()
                    code += sm.load_constant(x)
                    code += sm.load_constant(y)
                    code += sm.notequal()
                    out, dp, data = run(code)
                    self.assertEqual([int(x == y), int(x != y), 0, 0], data)
                    self.assertEqual(2, dp)

    def test_021_sm_put_character(self):
        sm = StackMachine()
        code = 'sm putc\n'
        ch = '@'
        code += sm.load_constant(ord(ch))
        code += sm.put_character()
        out, dp, data = run(code)
        self.assertEqual([0, 0], data)
        self.assertEqual(0, 0)
        self.assertEqual(ch, out)

    def test_022_sm_put_character(self):
        sm = StackMachine()
        code = 'sm putc\n'
        ch = '@'
        code += sm.load_constant(ord(ch))
        code += sm.put_character()
        out, dp, data = run(code)
        self.assertEqual([0, 0], data)
        self.assertEqual(0, dp)
        self.assertEqual(ch, out)

    def test_023_sm_get_character(self):
        sm = StackMachine()
        code = 'sm getc\n'
        ch = '@'
        code += sm.get_character()
        out, dp, data = run(code, ch)
        self.assertEqual([ord(ch), 0], data)
        self.assertEqual(1, dp)

    def test_024_sm_while1(self):
        sm = StackMachine()
        code = 'sm while1\n'
        debug = False
        code += sm.load_constant(ord('A'), debug)
        code += sm.load_variable(0, debug)
        code += sm.put_character(debug)
        code += sm.load_variable(0, debug)
        code += sm.load_constant(ord('Z'), debug)
        code += sm.notequal(debug)

        code += sm.begin_while(debug)
        code += sm.load_variable(0, debug)
        code += sm.load_constant(1, debug)
        code += sm.add(debug)
        code += sm.store_variable(0, debug)
        code += sm.load_variable(0, debug)
        code += sm.load_constant(ord('Z'), debug)
        code += sm.notequal(debug)
        code += sm.load_variable(0, debug)
        code += sm.put_character(debug)
        code += sm.end_while(debug)
        code += sm.load_constant(ord('\n'), debug)
        code += sm.put_character(debug)

        out, dp, data = run(code, dump=debug)
        self.assertEqual([ord('Z'), 0, 0, 0], data)
        self.assertEqual(1, dp)
        self.assertEqual('ABCDEFGHIJKLMNOPQRSTUVWXYZ\n', out)

    def test_025_sm_while2(self):
        sm = StackMachine()
        code = 'sm while2\n'
        debug = True
        ist = 'This is an input string.\n'
        code += sm.get_character(debug)
        code += sm.load_variable(0, debug)
        code += sm.put_character(debug)
        code += sm.load_constant(ord(ist[-1]), debug)
        code += sm.notequal(debug)

        code += sm.begin_while(debug)
        code += sm.get_character(debug)
        code += sm.load_variable(0, debug)
        code += sm.put_character(debug)
        code += sm.load_constant(ord(ist[-1]), debug)
        code += sm.notequal(debug)
        code += sm.end_while(debug)

        out, dp, data = run(code, ist, dump=False)
        self.assertEqual([0, 0, 0], data)
        self.assertEqual(0, dp)
        self.assertEqual(ist, out)

    def test_026_sm_while3(self):
        sm = StackMachine()
        code = 'sm while3\n'
        debug = False
        dump = False
        code += sm.load_constant(0, debug)
        code += sm.load_constant(0, debug)
        code += sm.load_variable(0, debug)
        code += sm.load_constant(25, debug)
        code += sm.notequal(debug)

        code += sm.begin_while(debug)
        code += sm.load_constant(0, debug)
        code += sm.store_variable(1, debug)
        code += sm.load_variable(1, debug)
        code += sm.load_constant(5, debug)
        code += sm.notequal(debug)

        code += sm.begin_while(debug)
        code += sm.load_variable(0, debug)
        code += sm.load_variable(1, debug)
        code += sm.add(debug)
        code += sm.load_constant(ord('A'), debug)
        code += sm.add(debug)
        code += sm.put_character(debug)
        code += sm.load_variable(1, debug)
        code += sm.load_constant(1, debug)
        code += sm.add(debug)
        code += sm.store_variable(1, debug)
        code += sm.load_variable(1, debug)
        code += sm.load_constant(5, debug)
        code += sm.notequal(debug)
        code += sm.end_while(debug)

        code += sm.load_constant(ord('\n'), debug)
        code += sm.put_character(debug)
        code += sm.load_variable(0, debug)
        code += sm.load_constant(5, debug)
        code += sm.add(debug)
        code += sm.store_variable(0, debug)
        code += sm.load_variable(0, debug)
        code += sm.load_constant(25, debug)
        code += sm.notequal(debug)
        code += sm.end_while(debug)

        out, dp, data = run(code, dump=dump)
        self.assertEqual([25, 5, 0, 0, 0], data)
        self.assertEqual(2, dp)
        self.assertEqual('ABCDE\nFGHIJ\nKLMNO\nPQRST\nUVWXY\n', out)

    def test_027_sm_greater_than1(self):
        sm = StackMachine()
        code = 'sm gt1\n'
        debug = False
        dump = False
        x, y = 255, 255
        code += sm.load_constant(x, debug)
        code += sm.load_constant(y, debug)
        code += sm.greater_than(debug)
        out, dp, data = run(code, dump=dump)
        self.assertEqual([int(x > y), 0, 0, 0, 0, 0], data)
        self.assertEqual(1, dp)

    def test_028_sm_greater_than2(self):
        sm = StackMachine()
        code = 'sm gt2\n'
        debug = False
        dump = False
        x, y = 0, 0
        code += sm.load_constant(x, debug)
        code += sm.load_constant(y, debug)
        code += sm.greater_than(debug)
        out, dp, data = run(code, dump=dump)
        self.assertEqual([int(x > y), 0, 0, 0, 0, 0], data)
        self.assertEqual(1, dp)

    def test_029_sm_greater_than3(self):
        sm = StackMachine()
        code = 'sm gt3\n'
        debug = False
        dump = False
        x, y = 10, 0
        code += sm.load_constant(x, debug)
        code += sm.load_constant(y, debug)
        code += sm.greater_than(debug)
        out, dp, data = run(code, dump=dump)
        self.assertEqual([int(x > y), 0, 0, 0, 0, 0], data)
        self.assertEqual(1, dp)

    def test_030_sm_greater_than4(self):
        sm = StackMachine()
        code = 'sm gt4\n'
        debug = False
        dump = False
        x, y = 0, 10
        code += sm.load_constant(x, debug)
        code += sm.load_constant(y, debug)
        code += sm.greater_than(debug)
        out, dp, data = run(code, dump=dump)
        self.assertEqual([int(x > y), 0, 0, 0, 0, 0], data)
        self.assertEqual(1, dp)

    def test_031_sm_less_than1(self):
        sm = StackMachine()
        code = 'sm lt1\n'
        debug = False
        dump = False
        x, y = 255, 255
        code += sm.load_constant(x, debug)
        code += sm.load_constant(y, debug)
        code += sm.less_than(debug)
        out, dp, data = run(code, dump=dump)
        self.assertEqual([int(x < y), 0, 0, 0, 0, 0], data)
        self.assertEqual(1, dp)

    def test_032_sm_less_than2(self):
        sm = StackMachine()
        code = 'sm lt2\n'
        debug = False
        dump = False
        x, y = 0, 0
        code += sm.load_constant(x, debug)
        code += sm.load_constant(y, debug)
        code += sm.less_than(debug)
        out, dp, data = run(code, dump=dump)
        self.assertEqual([int(x < y), 0, 0, 0, 0, 0], data)
        self.assertEqual(1, dp)

    def test_033_sm_less_than3(self):
        sm = StackMachine()
        code = 'sm lt1\n'
        debug = False
        dump = False
        x, y = 0, 10
        code += sm.load_constant(x, debug)
        code += sm.load_constant(y, debug)
        code += sm.less_than(debug)
        out, dp, data = run(code, dump=dump)
        self.assertEqual([int(x < y), 0, 0, 0, 0, 0], data)
        self.assertEqual(1, dp)

    def test_034_sm_less_than4(self):
        sm = StackMachine()
        code = 'sm lt2\n'
        debug = False
        dump = False
        x, y = 10, 0
        code += sm.load_constant(x, debug)
        code += sm.load_constant(y, debug)
        code += sm.less_than(debug)
        out, dp, data = run(code, dump=dump)
        self.assertEqual([int(x < y), 0, 0, 0, 0, 0], data)
        self.assertEqual(1, dp)

    def test_035_sm_compare_all(self):
        if TESTALL:
            debug = False
            dump = False
            for x in range(256):
                for y in range(256):
                    sm = StackMachine()
                    code = f'sm compare all {x} {y}\n'
                    code += sm.load_constant(x, debug)
                    code += sm.load_constant(y, debug)
                    code += sm.greater_than(debug)
                    code += sm.load_constant(x, debug)
                    code += sm.load_constant(y, debug)
                    code += sm.less_than(debug)
                    code += sm.load_constant(x, debug)
                    code += sm.load_constant(y, debug)
                    code += sm.greater_or_equal(debug)
                    code += sm.load_constant(x, debug)
                    code += sm.load_constant(y, debug)
                    code += sm.less_or_equal(debug)
                    out, dp, data = run(code, dump=dump)
                    self.assertEqual([int(x > y), int(x < y), int(x >= y), int(x <= y), 0, 0, 0, 0, 0], data)
                    self.assertEqual(4, dp)

    def test_036_sm_modulo1(self):
        sm = StackMachine()
        code = 'sm mod1\n'
        debug = False
        dump = False
        x, y = 20, 6
        code += sm.load_constant(x, debug)
        code += sm.load_constant(y, debug)
        code += sm.modulo(debug)
        out, dp, data = run(code, dump=dump)
        self.assertEqual([int(x % y), 0, 0, 0, 0, 0, 0, 0], data)
        self.assertEqual(1, dp)

    def test_037_sm_divide1(self):
        sm = StackMachine()
        code = 'sm mod1\n'
        debug = False
        dump = False
        x, y = 20, 6
        code += sm.load_constant(x, debug)
        code += sm.load_constant(y, debug)
        code += sm.divide(debug)
        out, dp, data = run(code, dump=dump)
        self.assertEqual([int(x // y), 0, 0, 0, 0, 0, 0, 0, 0], data)
        self.assertEqual(1, dp)

    def test_038_sm_divmod_all(self):
        if TESTALL:
            for x in range(256):
                for y in range(1, 256):
                    sm = StackMachine()
                    code = f'sm div mod all {x} {y}\n'
                    debug = False
                    dump = False
                    code += sm.load_constant(x, debug)
                    code += sm.load_constant(y, debug)
                    code += sm.modulo(debug)
                    code += sm.load_constant(x, debug)
                    code += sm.load_constant(y, debug)
                    code += sm.divide(debug)
                    out, dp, data = run(code, dump=dump)
                    self.assertEqual([int(x % y), int(x // y), 0, 0, 0, 0, 0, 0, 0, 0], data)
                    self.assertEqual(2, dp)

    def test_039_sm_if1(self):
        debug = False
        dump = False
        sm = StackMachine()
        code = 'sm if1\n'
        code += sm.load_constant(1, debug)
        code += sm.load_constant(10, debug)
        code += sm.less_than(debug)
        code += sm.begin_if(debug)
        code += sm.load_constant(ord('T'), debug)
        code += sm.put_character(debug)
        code += sm.begin_else(debug)
        code += sm.load_constant(ord('F'), debug)
        code += sm.put_character(debug)
        code += sm.end_if(debug)
        out, dp, data = run(code, dump=dump)
        self.assertEqual([0, 0, 0, 0, 0, 0], data)
        self.assertEqual(0, dp)
        self.assertEqual('T', out)
        self.assertEqual(sm.dp, dp)

    def test_040_sm_gcd1(self):
        debug = False
        dump = False
        x, y = 36, 12
        sm = StackMachine()
        code = 'sm gcd1\n'
        code += sm.load_constant(x, debug)
        code += sm.load_constant(y, debug)
        code += sm.load_variable(0, debug)
        code += sm.begin_while(debug)
        code += sm.load_variable(0, debug)
        code += sm.load_variable(1, debug)
        code += sm.less_than(debug)
        code += sm.begin_if(debug)
        code += sm.load_variable(0, debug)
        code += sm.load_variable(1, debug)
        code += sm.store_variable(0, debug)
        code += sm.store_variable(1, debug)
        code += sm.begin_else(debug)
        code += sm.end_if(debug)
        code += sm.load_variable(0, debug)
        code += sm.load_variable(1, debug)
        code += sm.subtract(debug)
        code += sm.store_variable(0, debug)
        code += sm.load_variable(0, debug)
        code += sm.end_while(debug)
        code += sm.load_variable(1, debug)
        code += sm.load_constant(ord('0'), debug)
        code += sm.add(debug)
        code += sm.put_character(debug)
        out, dp, data = run(code, dump=dump)
        self.assertEqual([0, math.gcd(x, y), 0, 0, 0, 0, 0, 0], data)
        self.assertEqual(sm.dp, dp)
        self.assertEqual(dp, 2)
        self.assertEqual(ord(out[0]), (math.gcd(x, y) + ord('0')) % 256)

    def test_041_sm_gcd2(self):
        debug = False
        dump = False
        x, y = 36, 12
        sm = StackMachine()
        code = 'sm gcd2\n'
        code += sm.load_constant(x, debug)
        code += sm.load_constant(y, debug)
        code += sm.load_variable(0, debug)
        code += sm.begin_while(debug)
        code += sm.load_variable(1, debug)
        code += sm.load_variable(0, debug)
        code += sm.modulo(debug)
        code += sm.store_variable(1, debug)
        code += sm.load_variable(0, debug)
        code += sm.load_variable(1, debug)
        code += sm.store_variable(0, debug)
        code += sm.store_variable(1, debug)
        code += sm.load_variable(0, debug)
        code += sm.end_while(debug)
        code += sm.load_variable(1, debug)
        code += sm.load_constant(ord('0'), debug)
        code += sm.add(debug)
        code += sm.put_character(debug)
        out, dp, data = run(code, dump=dump)
        self.assertEqual([0, math.gcd(x, y), 0, 0, 0, 0, 0, 0, 0, 0], data)
        self.assertEqual(sm.dp, dp)
        self.assertEqual(dp, 2)
        self.assertEqual(ord(out[0]), (math.gcd(x, y) + ord('0')) % 256)

    def test_042_sm_load_address(self):
        debug = False
        dump = False
        sm = StackMachine()
        length = 5
        address = 4
        code = f'sm la\n'
        for i in range(length)[::-1]:
            code += sm.load_constant(i, debug)
        code += sm.load_constant(0, debug)
        code += sm.load_constant(0, debug)
        code += sm.load_constant(0, debug)
        code += sm.load_constant(0, debug)
        code += sm.load_constant(address, debug)
        code += sm.load_address(length, debug)
        out, dp, data = run(code, dump=dump)
        self.assertEqual(list(range(length)[::-1]) + [0] * 4 + [address] + [0], data)
        self.assertEqual(dp, length + 4 + 1)
        self.assertEqual(dp, sm.dp)

    def test_043_sm_store_address(self):
        debug = False
        dump = False
        sm = StackMachine()
        length = 5
        address = 4
        code = f'sm sa\n'
        for i in range(length)[::-1]:
            code += sm.load_constant(i, debug)
        code += sm.load_constant(0, debug)
        code += sm.load_constant(0, debug)
        code += sm.load_constant(0, debug)
        code += sm.load_constant(0, debug)
        code += sm.load_constant(10, debug)
        code += sm.load_constant(address, debug)
        code += sm.store_address(length, debug)
        out, dp, data = run(code, dump=dump)
        arr = list(range(length)[::-1])
        arr[-address - 1] = 10
        arr += [0] * 4 + [0] * 3
        self.assertEqual(arr, data)
        self.assertEqual(length + 4, dp)
        self.assertEqual(sm.dp, dp)

    def test_044_sm_factor(self):
        debug = False
        dump = False
        target = 192
        assert target > 1
        sm = StackMachine()
        code = 'sm factor\n'
        # initialize
        for _ in range(10):
            code += sm.load_constant(0, debug)
        addr_ans = 10  # ans 10
        code += sm.load_constant(0, debug)
        code += sm.load_constant(0, debug)
        code += sm.load_constant(0, debug)
        code += sm.load_constant(0, debug)
        addr_div = sm.dp
        code += sm.load_constant(2, debug)  # div 14
        addr_target = sm.dp
        code += sm.load_constant(0, debug)  # target 15
        # parse input
        code += sm.load_constant(1, debug)
        code += sm.begin_while(debug)
        addr_in = sm.dp
        code += sm.get_character(debug)
        code += sm.load_variable(addr_in, debug)
        code += sm.load_constant(ord('\n'), debug)
        code += sm.notequal(debug)
        code += sm.begin_if(debug)
        code += sm.load_variable(addr_target, debug)
        code += sm.load_constant(10, debug)
        code += sm.multiply(debug)
        code += sm.load_variable(addr_in, debug)
        code += sm.load_constant(ord('0'), debug)
        code += sm.subtract(debug)
        code += sm.add(debug)
        code += sm.store_variable(addr_target, debug)
        code += sm.begin_else(debug)
        code += sm.end_if(debug)
        code += sm.load_constant(ord('\n'), debug)
        code += sm.notequal(debug)
        code += sm.end_while(debug)

        # print target
        code += sm.load_variable(addr_target, debug)
        code += sm.load_constant(100, debug)
        code += sm.greater_or_equal(debug)
        code += sm.begin_if(debug)
        code += sm.load_variable(addr_target, debug)
        code += sm.load_constant(100, debug)
        code += sm.divide(debug)
        code += sm.load_constant(ord('0'), debug)
        code += sm.add(debug)
        code += sm.put_character()
        code += sm.begin_else(debug)
        code += sm.end_if(debug)

        code += sm.load_variable(addr_target, debug)
        code += sm.load_constant(10, debug)
        code += sm.greater_or_equal(debug)
        code += sm.begin_if(debug)
        code += sm.load_variable(addr_target, debug)
        code += sm.load_constant(100, debug)
        code += sm.modulo(debug)
        code += sm.load_constant(10, debug)
        code += sm.divide(debug)
        code += sm.load_constant(ord('0'), debug)
        code += sm.add(debug)
        code += sm.put_character()
        code += sm.begin_else(debug)
        code += sm.end_if(debug)

        code += sm.load_variable(addr_target, debug)
        code += sm.load_constant(1, debug)
        code += sm.greater_or_equal(debug)
        code += sm.begin_if(debug)
        code += sm.load_variable(addr_target, debug)
        code += sm.load_constant(10, debug)
        code += sm.modulo(debug)
        code += sm.load_constant(ord('0'), debug)
        code += sm.add(debug)
        code += sm.put_character()
        code += sm.begin_else(debug)
        code += sm.end_if(debug)

        code += sm.load_constant(ord(' '), debug)
        code += sm.put_character()
        code += sm.load_constant(ord('='), debug)
        code += sm.put_character()
        code += sm.load_constant(ord(' '), debug)
        code += sm.put_character()

        # factorize
        addr_idx = sm.dp
        code += sm.load_constant(0, debug)  # idx 16
        code += sm.load_variable(addr_target, debug)
        code += sm.load_constant(1, debug)
        code += sm.notequal(debug)

        code += sm.begin_while(debug)
        code += sm.load_variable(addr_target, debug)
        code += sm.load_variable(addr_div, debug)
        code += sm.modulo(debug)

        code += sm.begin_if(debug)
        code += sm.load_variable(addr_div, debug)
        code += sm.load_constant(1, debug)
        code += sm.add()
        code += sm.store_variable(addr_div, debug)

        code += sm.begin_else(debug)

        code += sm.load_variable(addr_target, debug)
        code += sm.load_variable(addr_div, debug)
        code += sm.divide(debug)
        code += sm.store_variable(addr_target, debug)
        code += sm.load_variable(addr_div, debug)
        code += sm.load_variable(addr_idx, debug)
        code += sm.store_address(addr_ans, debug)
        code += sm.load_variable(addr_idx, debug)
        code += sm.load_constant(1, debug)
        code += sm.add(debug)
        code += sm.store_variable(addr_idx, debug)
        code += sm.end_if(debug)

        code += sm.load_variable(addr_target, debug)
        code += sm.load_constant(1, debug)
        code += sm.notequal(debug)

        code += sm.end_while(debug)

        # print result
        addr_acc = sm.dp
        code += sm.load_constant(0, debug)  # accessor
        code += sm.load_variable(addr_acc, debug)
        code += sm.load_variable(addr_idx, debug)
        code += sm.less_than(debug)

        code += sm.begin_while(debug)

        code += sm.load_variable(addr_acc, debug)
        code += sm.load_address(addr_ans, debug)
        code += sm.load_constant(100, debug)
        code += sm.greater_or_equal(debug)
        code += sm.begin_if(debug)
        code += sm.load_variable(addr_acc, debug)
        code += sm.load_address(addr_ans, debug)
        code += sm.load_constant(100, debug)
        code += sm.divide(debug)
        code += sm.load_constant(ord('0'), debug)
        code += sm.add(debug)
        code += sm.put_character()
        code += sm.begin_else(debug)
        code += sm.end_if(debug)

        code += sm.load_variable(addr_acc, debug)
        code += sm.load_address(addr_ans, debug)
        code += sm.load_constant(10, debug)
        code += sm.greater_or_equal(debug)
        code += sm.begin_if(debug)
        code += sm.load_variable(addr_acc, debug)
        code += sm.load_address(addr_ans, debug)
        code += sm.load_constant(100, debug)
        code += sm.modulo(debug)
        code += sm.load_constant(10, debug)
        code += sm.divide(debug)
        code += sm.load_constant(ord('0'), debug)
        code += sm.add(debug)
        code += sm.put_character()
        code += sm.begin_else(debug)
        code += sm.end_if(debug)

        code += sm.load_variable(addr_acc, debug)
        code += sm.load_address(addr_ans, debug)
        code += sm.load_constant(1, debug)
        code += sm.greater_or_equal(debug)
        code += sm.begin_if(debug)
        code += sm.load_variable(addr_acc, debug)
        code += sm.load_address(addr_ans, debug)
        code += sm.load_constant(10, debug)
        code += sm.modulo(debug)
        code += sm.load_constant(ord('0'), debug)
        code += sm.add(debug)
        code += sm.put_character()
        code += sm.begin_else(debug)
        code += sm.end_if(debug)

        code += sm.load_variable(addr_acc, debug)
        code += sm.load_constant(1, debug)
        code += sm.add(debug)
        code += sm.store_variable(addr_acc, debug)

        code += sm.load_variable(addr_acc, debug)
        code += sm.load_variable(addr_idx, debug)
        code += sm.notequal(debug)
        code += sm.begin_if(debug)
        code += sm.load_constant(ord(' '), debug)
        code += sm.put_character(debug)
        code += sm.load_constant(ord('*'), debug)
        code += sm.put_character(debug)
        code += sm.load_constant(ord(' '), debug)
        code += sm.put_character(debug)
        code += sm.begin_else(debug)
        code += sm.end_if(debug)

        code += sm.load_variable(addr_acc, debug)
        code += sm.load_variable(addr_idx, debug)
        code += sm.less_than(debug)
        code += sm.end_while(debug)

        code += sm.load_constant(ord('\n'), debug)
        code += sm.put_character(debug)

        ist = f'{target}\n'
        out, dp, data = run(code, input_string=ist, dump=dump)

        def factor(num):
            ans = []
            div = 2
            while num != 1:
                if num % div:
                    div += 1
                else:
                    num = num // div
                    ans += [div]
            return ans

        self.assertEqual(sm.dp, dp)
        self.assertEqual(f'{target} = {" * ".join(map(str, factor(target)))}\n', out)

    def test_045_sm_boolor(self):
        debug = False
        dump = False
        for x in range(3):
            for y in range(3):
                sm = StackMachine()
                code = f'sm boolor {x} {y}\n'
                code += sm.load_constant(x, debug)
                code += sm.load_constant(y, debug)
                code += sm.boolor()
                out, dp, data = run(code, dump=dump)
                self.assertEqual(1, dp)
                self.assertEqual([int(bool(x) or bool(y)), 0, 0, 0], data)

    def test_046_sm_booland(self):
        debug = False
        dump = False
        for x in range(3):
            for y in range(3):
                sm = StackMachine()
                code = f'sm booland {x} {y}\n'
                code += sm.load_constant(x, debug)
                code += sm.load_constant(y, debug)
                code += sm.booland()
                out, dp, data = run(code, dump=dump)
                self.assertEqual(1, dp)
                self.assertEqual([int(bool(x) and bool(y)), 0, 0, 0], data)

    def test_047_sm_clean(self):
        debug = False
        dump = False
        sm = StackMachine()
        code = ''
        begin, end = 10, 20
        for i in range(end):
            code += sm.load_constant(i, debug)
        code += sm.clean(10, 20, debug)
        out, dp, data = run(code, dump=dump)
        self.assertEqual(20, dp)
        self.assertEqual(list(range(10)) + [0] * 11, data)

    def test_048_sm_put_array(self):
        debug = False
        dump = False
        string = 'voidhoge'
        sm = StackMachine()
        code = 'sm puta'
        code += sm.load_constant(0, debug)
        for i, ch in enumerate(string[::-1]):
            code += sm.load_constant(ord(ch), debug)
        pos = sm.dp
        code += sm.load_constant(0, debug)
        code += sm.load_constant(0, debug)
        code += sm.load_constant(0, debug)
        code += sm.load_constant(0, debug)
        code += sm.put_array(pos, debug)
        out, dp, data = run(code, dump=dump)
        self.assertEqual(out, string)
        self.assertEqual(sm.dp, dp)
        self.assertEqual(dp, len(string) + 5)
        self.assertEqual([0] + list(map(ord, string[::-1])) + [0, 0, 0, 0, 0], data)

    def test_049_sm_multi_dim_load(self):
        debug = False
        dump = False
        sm = StackMachine()
        code = 'sm multidimload'
        shape = (5,4,3)
        testdata = []

        def initialize(idx, shape, dim):
            nonlocal code
            nonlocal sm
            nonlocal testdata
            if dim == len(shape) - 1:
                for i in range(shape[dim]):
                    code += sm.load_constant(idx * shape[dim] + i + 10, debug)
                    testdata += [idx * shape[dim] + i + 10]
                for _ in range(4):
                    code += sm.load_constant(0, debug)
                    testdata += [0]
            else:
                for i in range(shape[dim]):
                    initialize(idx * shape[dim] + i, shape, dim + 1)
            if dim != 0:
                code += sm.load_constant(0, debug)
                testdata += [0]

        initialize(0, shape, 0)
        pos = sm.dp
        code += sm.load_constant(ord('a'), debug)
        code += sm.load_constant(ord('a'), debug)
        code += sm.load_constant(ord('a'), debug)
        testdata += [ord('a')] * 3
        for p in shape[::-1]:
            code += sm.load_constant(p - 1, debug)

        code += sm.multi_dim_load(pos, shape, debug)
        testdata += [10]
        testdata += [0] * len(shape)
        out, dp, data = run(code, dump=dump)
        print(f'pos: {pos}')

        m = 33
        for begin in range(0, len(data), m):
            for i in range(m):
                print(f'{begin + i:3}', end='')
            print()
            for i in data[begin:begin+m]:
                print(f'{i:3}', end='')
            print()
        self.assertEqual(data, testdata)
        self.assertEqual(dp, sm.dp)

    def test_050_sm_multi_dim_store(self):
        debug = False
        dump = False
        sm = StackMachine()
        code = 'sm multidimload'
        shape = (5,4,3)
        testdata = []

        def initialize(idx, shape, dim):
            nonlocal code
            nonlocal sm
            nonlocal testdata
            if dim == len(shape) - 1:
                for i in range(shape[dim]):
                    code += sm.load_constant(idx * shape[dim] + i + 10, debug)
                    testdata += [idx * shape[dim] + i + 10]
                for _ in range(4):
                    code += sm.load_constant(0, debug)
                    testdata += [0]
            else:
                for i in range(shape[dim]):
                    initialize(idx * shape[dim] + i, shape, dim + 1)
            if dim != 0:
                code += sm.load_constant(0, debug)
                testdata += [0]
        initialize(0, shape, 0)
        pos = sm.dp
        code += sm.load_constant(ord('a'), debug)
        code += sm.load_constant(ord('a'), debug)
        code += sm.load_constant(ord('a'), debug)
        testdata += [ord('a')] * 3
        for p in shape[::-1]:
            code += sm.load_constant(p - 1, debug)
        code += sm.load_constant(99, debug)

        code += sm.multi_dim_store(pos, shape, debug)
        testdata += [0] * (len(shape) + 2)
        testdata[0] = 99
        out, dp, data = run(code, dump=dump)
        print(f'pos: {pos}')

        m = 33
        for begin in range(0, len(data), m):
            for i in range(m):
                print(f'{begin + i:3}', end='')
            print()
            for i in data[begin:begin+m]:
                print(f'{i:3}', end='')
            print()
            print()
        self.assertEqual(data, testdata)
        self.assertEqual(dp, sm.dp)


if __name__ == '__main__':
    unittest.main()
