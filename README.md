# Brainfuck Compiler

## Items
- Brainfuck Interpreter: `interpreter.py`
- Lexical Analyzer: `lexer.py`
- Parser (main part of the compiler): `parser.py`
- Compiler: `compiler.py`
- Stack Machine Assembler: `stack_machine.py`
- Examples: `data/`

## Usage
```shellsession
$ git clone https://github.com/brainfuck.git
$ cd brainfuck
$ cat data/for.txt
for (var i = 'a'; i <= 'z'; i += 1) {
    putchar(i);
}
putchar('\n');
$ ./compiler.py data/for.txt | tee data/for.bf
[-]>[-]+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
++++++++++++++++++++++++><<[-]>[-<+>]>[-]<<[->+>+<<]>>[-<<+>>][-]+++++++++++++++
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
+++++++++++++++++++++++++++>[-]>[-]+>[-]+>[-]<[<<<<[>]>>>[->]<<<<-<->>>>]<[-]<<+
[-]<+[[-]>+<]>[-<+>][-]+<[[-]>-<]>[-<+>]<[[-]>[-]<<[->+>+<<]>>[-<<+>>]<.[-]>[-]<
<[->+>+<<]>>[-<<+>>][-]+><[-<+>]<<[-]>[-<+>]>[-]<<[->+>+<<]>>[-<<+>>][-]++++++++
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
++++++++++++++++++++++++++++++++++>[-]>[-]+>[-]+>[-]<[<<<<[>]>>>[->]<<<<-<->>>>]
<[-]<<+[-]<+[[-]>+<]>[-<+>][-]+<[[-]>-<]>[-<+>]<]<[-][-]++++++++++><.[-]

$ ./interpreter.py data/for.bf
abcdefghijklmnopqrstuvwxyz
(0, [0, 0, 0, 0, 0, 0, 0], 237677)
$ 
```

## Author
- Mugi Noda (void-hoge)

## License
- GPLv3
