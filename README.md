# Brainfuck Compiler

## Items
- Brainfuck Interpreter: `src/bfcc/interpreter.py`
- Lexical Analyzer: `src/bfcc/lexer.py`
- Parser (main part of the compiler): `src/bfcc/parser.py`
- Compiler: `src/bfcc/compiler.py`
- Stack Machine Assembler: `src/bfcc/stack_machine.py`
- Examples: `data/`

## Usage
```shellsession
$ git clone https://github.com/brainfuck.git
$ cd brainfuck
$ python3 -m pip install -e .
$ cat data/for.txt
for (var i = 'a'; i <= 'z'; i += 1) {
    putchar(i);
}
putchar('\n');
$ bfcc data/for.txt | tee data/for.bf
[-]>[-]+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
++++++++++++++++++++++++><<[-]>[-<+>]>[-]<<[->+>+<<]>>[-<<+>>][-]+++++++++++++++
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
+++++++++++++++++++++++++++>[-]>[-]+>[-]+>[-]<[<<<<[>]>>>[->]<<<<-<->>>>]<[-]<<+
[-]<+[[-]>+<]>[-<+>][-]+<[[-]>-<]>[-<+>]<[[-]>[-]<<[->+>+<<]>>[-<<+>>]<.[-]>[-]<
<[->+>+<<]>>[-<<+>>][-]+><[-<+>]<<[-]>[-<+>]>[-]<<[->+>+<<]>>[-<<+>>][-]++++++++
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
++++++++++++++++++++++++++++++++++>[-]>[-]+>[-]+>[-]<[<<<<[>]>>>[->]<<<<-<->>>>]
<[-]<<+[-]<+[[-]>+<]>[-<+>][-]+<[[-]>-<]>[-<+>]<]<[-][-]++++++++++><.[-]

$ python3 -m bfcc.interpreter data/for.bf
abcdefghijklmnopqrstuvwxyz
(0, [0, 0, 0, 0, 0, 0, 0], 237677)
$ 
```

Compile from stdin and write to a file:

```shellsession
$ cat data/for.txt | bfcc - -o data/for.bf
```

## Language Specification

### 1. Overview
- This language is a compact C-like language compiled to Brainfuck.
- Programs are written as a sequence of statements.
- User-defined functions are not supported.

### 2. Declarations
- Variable declaration:
  - `var x;`
  - `var x = expr;`
- Array declaration (multi-dimensional):
  - `arr a[dim1][dim2]...;`

### 3. Statements
- Declaration statements:
  - `var ...;`
  - `arr ...;`
- Assignment statements:
  - `=`, `+=`, `-=`, `*=`, `/=`, `%=`
  - Examples: `x = 1;`, `x += 2;`, `a[i] %= 3;`
- Control flow:
  - `if (cond) { ... }`
  - `if (cond) { ... } else { ... }`
  - `while (cond) { ... }`
  - `for (init; cond; reinit) { ... }`
- Call statements:
  - `putchar(x);`
  - `putint(x);`
  - Other calls are parsed as function calls, but only built-ins are valid.

### 4. `for` Statement Details
- Form: `for (init; cond; reinit) { ... }`
- `init`:
  - supports variable declarations, array declarations, and assignments
  - comma-separated multiple entries are allowed
- `reinit`:
  - supports assignments
  - comma-separated multiple entries are allowed
  - Example: `for (var i = 0, j = 10; i < j; i += 1, j -= 1) { ... }`

### 5. Expressions
- Supported operands:
  - Integer literals (e.g. `123`)
  - Character literals (e.g. `'a'`, `'\n'`, `'\x41'`)
  - Variables (e.g. `x`)
  - Array elements (e.g. `a[i][j]`)
  - Built-in function calls (`getchar()`, `getint()`)
- Operators:
  - Arithmetic: `+`, `-`, `*`, `/`, `%`
  - Comparison: `==`, `!=`, `<`, `<=`, `>`, `>=`
  - Logical/bit-like: `!`, `&`, `|`
  - Unary: `+`, `-`, `!`
- Parentheses `(...)` are supported.
- Operator precedence is C-like (`* / %` > `+ -` > comparisons > `&` > `|`).

### 6. Built-in Functions
- Input (expression context):
  - `getchar()` : reads one character
  - `getint()` : reads decimal digits and returns an integer
- Output (statement context):
  - `putchar(x)` : outputs one character
  - `putint(x)` : outputs an integer in decimal
- Any other function name is treated as undefined.

### 7. Lexical Rules
- Identifiers:
  - start with `[A-Za-z_]`
  - continue with `[A-Za-z0-9_]*`
- Keywords:
  - `while`, `if`, `else`, `for`, `var`, `arr`
- Comments:
  - line comment: `// ...`
  - block comment: `/* ... */`
- Unclosed block comments are syntax errors.

### 8. Scope and Static Checks
- Block scope is used (`{ ... }` introduces a local scope).
- Redeclaring the same name in the same scope is an error.
- Array indexing must match declared dimensions.
- Using a variable as an array (or vice versa) is an error.

### 9. Runtime Model Notes
- Values are handled as 1-byte cells (0 to 255 with wraparound behavior).
- Arithmetic should be designed with wraparound semantics in mind.

## Author
- Mugi Noda (void-hoge)

## License
- GPLv3
