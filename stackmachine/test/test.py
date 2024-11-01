#!/usr/bin/env pyton3

import unittest
from stack_machine import *
from interpreter import *
import io


def run(code, input_string='', dump=False):
    ist = io.StringIO(input_string)
    ost = io.StringIO()
    print()
    print(code)
    dp, data, step = interpreter(code, ist, ost, dump)
    print(f'Execution successfully finished in {step} steps.')
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
        self.assertEqual([255,0,0,0], data)
        self.assertEqual(1, dp)

    def test_010_sm_bool1(self):
        sm = StackMachine()
        code = 'sm bool1\n'
        code += sm.load_constant(10)
        code += sm.boolean()
        out, dp, data = run(code)
        self.assertEqual([1, 0], data)
        self.assertEqual(1, dp)

    def test_011_sm_bool2(self):
        sm = StackMachine()
        code = 'sm bool2\n'
        code += sm.load_constant(0)
        code += sm.boolean()
        out, dp, data = run(code)
        self.assertEqual([0, 0], data)
        self.assertEqual(1, dp)

    def test_012_sm_boolnot1(self):
        sm = StackMachine()
        code = 'sm not1\n'
        code += sm.load_constant(0)
        code += sm.boolnot()
        out, dp, data = run(code)
        self.assertEqual([1, 0], data)
        self.assertEqual(1, dp)

    def test_013_sm_boolnot2(self):
        sm = StackMachine()
        code = 'sm not2\n'
        code += sm.load_constant(10)
        code += sm.boolnot()
        out, dp, data = run(code)
        self.assertEqual([0, 0], data)
        self.assertEqual(1, dp)

    def test_014_sm_equal1(self):
        sm = StackMachine()
        code = 'sm equal1\n'
        code += sm.load_constant(10)
        code += sm.load_constant(10)
        code += sm.equal()
        out, dp, data = run(code)
        self.assertEqual([1, 0, 0], data)
        self.assertEqual(1, dp)

    def test_015_sm_equal2(self):
        sm = StackMachine()
        code = 'sm equal2\n'
        code += sm.load_constant(10)
        code += sm.load_constant(5)
        code += sm.equal()
        out, dp, data = run(code)
        self.assertEqual([0, 0, 0], data)
        self.assertEqual(1, dp)

    def test_016_sm_equal1(self):
        sm = StackMachine()
        code = 'sm neq1\n'
        code += sm.load_constant(10)
        code += sm.load_constant(10)
        code += sm.notequal()
        out, dp, data = run(code)
        self.assertEqual([0, 0, 0], data)
        self.assertEqual(1, dp)

    def test_017_sm_equal2(self):
        sm = StackMachine()
        code = 'sm neq2\n'
        code += sm.load_constant(10)
        code += sm.load_constant(5)
        code += sm.notequal()
        out, dp, data = run(code)
        self.assertEqual([1, 0, 0], data)
        self.assertEqual(1, dp)

    def test_018_sm_put_character(self):
        sm = StackMachine()
        code = 'sm putc\n'
        ch = '@'
        code += sm.load_constant(ord(ch))
        code += sm.put_character()
        out, dp, data = run(code)
        self.assertEqual([0, 0], data)
        self.assertEqual(0, 0)
        self.assertEqual(ch, out)

    def test_019_sm_put_character(self):
        sm = StackMachine()
        code = 'sm putc\n'
        ch = '@'
        code += sm.load_constant(ord(ch))
        code += sm.put_character()
        out, dp, data = run(code)
        self.assertEqual([0, 0], data)
        self.assertEqual(0, dp)
        self.assertEqual(ch, out)

    def test_020_sm_get_character(self):
        sm = StackMachine()
        code = 'sm getc\n'
        ch = '@'
        code += sm.get_character()
        out, dp, data = run(code, ch)
        self.assertEqual([ord(ch), 0], data)
        self.assertEqual(1, dp)

    def test_021_sm_while1(self):
        sm = StackMachine()
        code = 'sm while1\n'
        debug = False
        code += sm.load_constant(ord('A'), debug)
        code += sm.load_variable(0, debug)
        code += sm.put_character(debug)
        code += sm.load_variable(0, debug)
        code += sm.load_constant(ord('Z'), debug)
        code += sm.notequal(debug)

        code += sm.beginwhile(debug)
        code += sm.load_variable(0, debug)
        code += sm.load_constant(1, debug)
        code += sm.add(debug)
        code += sm.store_variable(0, debug)
        code += sm.load_variable(0, debug)
        code += sm.load_constant(ord('Z'), debug)
        code += sm.notequal(debug)
        code += sm.load_variable(0, debug)
        code += sm.put_character(debug)
        code += sm.endwhile(debug)
        code += sm.load_constant(ord('\n'), debug)
        code += sm.put_character(debug)

        out, dp, data = run(code, dump=debug)
        self.assertEqual([ord('Z'), 0, 0, 0], data)
        self.assertEqual(1, dp)
        self.assertEqual('ABCDEFGHIJKLMNOPQRSTUVWXYZ\n', out)

    def test_022_sm_while2(self):
        sm = StackMachine()
        code = 'sm while2\n'
        debug = True
        ist = 'This is an input string.\n'
        code += sm.get_character(debug)
        code += sm.load_variable(0, debug)
        code += sm.put_character(debug)
        code += sm.load_constant(ord(ist[-1]), debug)
        code += sm.notequal(debug)

        code += sm.beginwhile(debug)
        code += sm.get_character(debug)
        code += sm.load_variable(0, debug)
        code += sm.put_character(debug)
        code += sm.load_constant(ord(ist[-1]), debug)
        code += sm.notequal(debug)
        code += sm.endwhile(debug)

        out, dp, data = run(code, ist, dump=False)
        self.assertEqual([0, 0, 0], data)
        self.assertEqual(0, dp)
        self.assertEqual(ist, out)

    def test_023_sm_while3(self):
        sm = StackMachine()
        code = 'sm while3\n'
        debug = False
        dump = False
        code += sm.load_constant(0, debug)
        code += sm.load_constant(0, debug)
        code += sm.load_variable(0, debug)
        code += sm.load_constant(25, debug)
        code += sm.notequal(debug)

        code += sm.beginwhile(debug)
        code += sm.load_constant(0, debug)
        code += sm.store_variable(1, debug)
        code += sm.load_variable(1, debug)
        code += sm.load_constant(5, debug)
        code += sm.notequal(debug)

        code += sm.beginwhile(debug)
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
        code += sm.endwhile(debug)

        code += sm.load_constant(ord('\n'), debug)
        code += sm.put_character(debug)
        code += sm.load_variable(0, debug)
        code += sm.load_constant(5, debug)
        code += sm.add(debug)
        code += sm.store_variable(0, debug)
        code += sm.load_variable(0, debug)
        code += sm.load_constant(25, debug)
        code += sm.notequal(debug)
        code += sm.endwhile(debug)

        out, dp, data = run(code, dump=dump)
        self.assertEqual([25, 5, 0, 0, 0], data)
        self.assertEqual(2, dp)
        self.assertEqual('ABCDE\nFGHIJ\nKLMNO\nPQRST\nUVWXY\n', out)

    def test_024_sm_greater_than1(self):
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

    def test_025_sm_greater_than2(self):
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

    def test_026_sm_greater_than3(self):
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

    def test_027_sm_greater_than4(self):
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

    def test_028_sm_less_than1(self):
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

    def test_029_sm_less_than2(self):
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

    def test_030_sm_less_than3(self):
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

    def test_031_sm_less_than4(self):
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

    def test_032_sm_greater_or_equal_all(self):
        for x in range(256):
            for y in range(256):
                sm = StackMachine()
                code = f'sm ge all {x} {y}\n'
                debug = False
                dump = False
                code += sm.load_constant(x, debug)
                code += sm.load_constant(y, debug)
                code += sm.greater_or_equal(debug)
                out, dp, data = run(code, dump=dump)
                self.assertEqual([int(x >= y), 0, 0, 0, 0, 0], data)
                self.assertEqual(1, dp)

    def test_033_sm_less_or_equal_all(self):
        for x in range(256):
            for y in range(256):
                sm = StackMachine()
                code = f'sm le all {x} {y}\n'
                debug = False
                dump = False
                code += sm.load_constant(x, debug)
                code += sm.load_constant(y, debug)
                code += sm.less_or_equal(debug)
                out, dp, data = run(code, dump=dump)
                self.assertEqual([int(x <= y), 0, 0, 0, 0, 0], data)
                self.assertEqual(1, dp)

if __name__ == '__main__':
    unittest.main()
