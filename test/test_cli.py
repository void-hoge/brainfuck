import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from bfcc.cli import main
from bfcc.compiler import compile_source


class TestCli(unittest.TestCase):
    def test_compile_to_stdout(self):
        source = "putchar('A');\n"
        expected = compile_source(source)
        stdout = io.StringIO()
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / 'input.txt'
            input_path.write_text(source, encoding='utf-8')
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = main([str(input_path)])
        self.assertEqual(0, code)
        self.assertEqual('', stderr.getvalue())
        self.assertEqual(expected, stdout.getvalue())

    def test_compile_to_file(self):
        source = "putchar('B');\n"
        expected = compile_source(source)
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / 'input.txt'
            output_path = Path(tmpdir) / 'out.bf'
            input_path.write_text(source, encoding='utf-8')

            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = main([str(input_path), '-o', str(output_path)])
            self.assertEqual(0, code)
            self.assertEqual('', stderr.getvalue())
            self.assertEqual(expected, output_path.read_text(encoding='utf-8'))

    def test_missing_input_file(self):
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = main(['/tmp/does-not-exist.bfcc-source'])
        self.assertEqual(1, code)
        self.assertIn('bfcc: error:', stderr.getvalue())
