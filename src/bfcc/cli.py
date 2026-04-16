#!/usr/bin/env python3

import argparse
import sys

from .compiler import compile_source


def build_parser():
    parser = argparse.ArgumentParser(description='Compile source code into Brainfuck.')
    parser.add_argument(
        'input',
        nargs='?',
        default='-',
        help='Input source file path. Use - to read from stdin.',
    )
    parser.add_argument(
        '-o',
        '--output',
        default='-',
        help='Output file path. Use - to write to stdout.',
    )
    parser.add_argument('--debug', action='store_true', help='Emit debug-friendly output.')
    return parser


def _read_source(path):
    if path == '-':
        return sys.stdin.read()
    with open(path, encoding='utf-8') as file:
        return file.read()


def _write_output(path, code):
    if path == '-':
        sys.stdout.write(code)
        return
    with open(path, 'w', encoding='utf-8') as file:
        file.write(code)


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        source = _read_source(args.input)
        code = compile_source(source, debug=args.debug)
        _write_output(args.output, code)
    except (OSError, RuntimeError, SyntaxError, AssertionError, IndexError) as exc:
        print(f'bfcc: error: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
