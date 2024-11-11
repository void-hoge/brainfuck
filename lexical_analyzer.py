#!/usr/bin/env python3

import re
import sys
from enum import IntEnum, auto


class Token(IntEnum):
    ID = auto()  # abc
    INT = auto()  # 123
    CHAR = auto()  # 'a'
    KW_WHILE = auto()  # while
    KW_IF = auto()  # if
    KW_ELSE = auto()  # else
    AND = auto()  # &
    OR = auto()  # |
    NOT = auto()  # !
    PLUS = auto()  # +
    MINUS = auto()  # -
    STAR = auto()  # *
    SLASH = auto()  # /
    PERCENT = auto()  # %
    ASSIGN = auto()  # =
    ADDASSIGN = auto()  # +=
    SUBASSIGN = auto()  # -=
    MULASSIGN = auto()  # *=
    DIVASSIGN = auto()  # /=
    MODASSIGN = auto()  # %=
    EQ = auto()  # ==
    NEQ = auto()  # !=
    GT = auto()  # >
    GE = auto()  # >=
    LT = auto()  # <
    LE = auto()  # <=
    COMMA = auto()  # ,
    SEMICOLON = auto()  # ;
    LPAREN = auto()  # (
    RPAREN = auto()  # )
    LBRACE = auto()  # {
    RBRACE = auto()  # }
    LBRACK = auto()  # [
    RBRACK = auto()  # ]
    EOF = auto()


class LexicalAnalyzer:
    def __init__(self, string):
        self.string = string
        self.pos = 0
        self.readingpos = 0
        self.tokens = []
        self.linecount = 0
        self.analyze()

    def skipspace(self):
        while self.pos < len(self.string) and self.string[self.pos] in ' \n\t\r':
            if self.string[self.pos] == '\n':
                self.linecount += 1
            self.pos += 1

    def get(self):
        if match := re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)', self.string[self.pos :]):
            head = match.group(1)
            self.pos += len(head)
            if head in ['while', 'if', 'else']:
                t = {
                    'while': Token.KW_WHILE,
                    'if': Token.KW_IF,
                    'else': Token.KW_ELSE,
                }[head]
                return {
                    'type': t,
                    'val': None,
                    'line': self.linecount,
                    'token': head,
                }
            else:
                return {
                    'type': Token.ID,
                    'val': None,
                    'line': self.linecount,
                    'token': head,
                }
        elif match := re.match('^(\d+[a-zA-Z_]+)', self.string[self.pos :]):
            raise RuntimeError(f'Undefined token at line {self.linecount}: {match.group(1)}')
        elif match := re.match(r'^(\d+)', self.string[self.pos :]):
            head = match.group(1)
            self.pos += len(head)
            return {
                'type': Token.INT,
                'val': int(head),
                'line': self.linecount,
                'token': head,
            }
        elif match := re.match(r"^'([^'\\]|\\[abfnrtv'\"\\?0-7]|\\x[0-9A-Fa-f]{1,2})'", self.string[self.pos :]):
            head = match.group(1)
            self.pos += len(head) + 2
            return {'type': Token.CHAR, 'val': ord(eval(f"'{head}'")), 'line': self.linecount, 'token': f"'{head}'"}
        elif match := re.match(
            r'^(&|\||!=|!|\+=|\+|-=|-|\*=|\*|\/=|\/|%=|%|==|=|>=|<=|>|<|,|;|\(|\)|\{|\}|\[|\])',
            self.string[self.pos :],
        ):
            head = match.group(1)
            self.pos += len(head)
            t = {
                '&': Token.AND,
                '|': Token.OR,
                '!': Token.NOT,
                '+': Token.PLUS,
                '-': Token.MINUS,
                '*': Token.STAR,
                '/': Token.SLASH,
                '%': Token.PERCENT,
                '=': Token.ASSIGN,
                '+=': Token.ADDASSIGN,
                '-=': Token.SUBASSIGN,
                '*=': Token.MULASSIGN,
                '/=': Token.DIVASSIGN,
                '%=': Token.MODASSIGN,
                '==': Token.EQ,
                '!=': Token.NEQ,
                '>': Token.GT,
                '>=': Token.GE,
                '<': Token.LT,
                '<=': Token.LE,
                ',': Token.COMMA,
                ';': Token.SEMICOLON,
                '(': Token.LPAREN,
                ')': Token.RPAREN,
                '{': Token.LBRACE,
                '}': Token.RBRACE,
                '[': Token.LBRACK,
                ']': Token.RBRACK,
            }[head]
            return {'type': t, 'val': None, 'line': self.linecount, 'token': head}
        elif self.pos >= len(self.string):
            return
        else:
            raise RuntimeError(f'Undefined token at line {self.linecount}: {self.string[self.pos:self.pos + 10]}')

    def analyze(self):
        self.skipspace()
        while token := self.get():
            self.skipspace()
            self.tokens += [token]
        self.tokens += [
            {
                'type': Token.EOF,
                'val': None,
                'line': self.linecount,
                'token': None,
            }
        ]

    def peek(self):
        if self.readingpos < len(self.tokens):
            return self.tokens[self.readingpos]
        else:
            return None

    def seek(self):
        self.readingpos += 1

    def unseek(self):
        self.readingpos -= 1


if __name__ == '__main__':
    with open(sys.argv[1]) as f:
        lex = LexicalAnalyzer(f.read())
    lex.analyze()
    for i, token in enumerate(lex.tokens):
        print(i, token)
