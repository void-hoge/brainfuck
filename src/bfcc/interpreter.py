#!/usr/bin/env python3

import sys

DUMPRANGE = 20


def interpreter(rawprog, ist=sys.stdin, ost=sys.stdout, dump=False):
    prog = ''.join([ch for ch in rawprog if ch != '\n'])
    ip = 0
    dp = 0
    maxdp = 0
    data = [0] * (1 << 16)
    step = 0
    while ip < len(prog):
        step += prog[ip] in '+-<>.,[]'
        if dump:
            print(prog[max(0, ip - DUMPRANGE) : ip + DUMPRANGE + 1])
            print(' ' * (min(DUMPRANGE, ip)) + '^')
            print(f'inst: {prog[ip]}')
            print(f'ip  : {ip}')
            print(f'data: {data[0 : maxdp + 1]}')
            print(f'dp  : {dp}')
            print()
        if prog[ip] == '>':
            dp += 1
            maxdp = max(maxdp, dp)
            if dp >= len(data):
                raise IndexError(f'data pointer out of range. (dp, ip, step) = ({dp}, {ip}, {step})')
        elif prog[ip] == '<':
            dp -= 1
            if dp < 0:
                raise IndexError(f'data pointer out of range. (dp, ip, step) = ({dp}, {ip}, {step})')
        elif prog[ip] == '+':
            data[dp] = (data[dp] + 1) & 0xFF
        elif prog[ip] == '-':
            data[dp] = (data[dp] - 1) & 0xFF
        elif prog[ip] == '.':
            print(chr(data[dp]), end='', file=ost, flush=True)
        elif prog[ip] == ',':
            data[dp] = ord(ist.read(1))
        elif prog[ip] == '[':
            if data[dp] == 0:
                cnt = 1
                while cnt:
                    ip += 1
                    if prog[ip] == '[':
                        cnt += 1
                        maxdp = max(maxdp, dp)
                    elif prog[ip] == ']':
                        cnt -= 1
        elif prog[ip] == ']':
            if data[dp] != 0:
                cnt = 1
                while cnt:
                    ip -= 1
                    if prog[ip] == ']':
                        cnt += 1
                        maxdp = max(maxdp, dp)
                    elif prog[ip] == '[':
                        cnt -= 1
        elif prog[ip] == '@':  # breakpoint
            return dp, data[0 : maxdp + 1], step
        ip += 1
    return dp, data[0 : maxdp + 1], step


if __name__ == '__main__':
    with open(sys.argv[1]) as f:
        print(interpreter(rawprog=f.read()))
