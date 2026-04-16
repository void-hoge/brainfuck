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

## Author
- Mugi Noda (void-hoge)

## License
- GPLv3
