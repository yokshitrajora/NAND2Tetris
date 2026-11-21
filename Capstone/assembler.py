#!/usr/bin/env python3
"""
assembler.py - a small Hack assembler (Nand to Tetris, project 6).

Usage:
    python assembler.py Prog.asm            # writes Prog.hack next to it
    python assembler.py Prog.asm -o out.hack

Two passes:
    First reading : strip comments/blank lines, record where each (LABEL) is.
    Second reading: translate every line into 16 bits; new variables get
                    RAM addresses 16, 17, 18, ...

Extra feature for K = 13 (K mod 3 = 1):
    A wrong line does not crash the assembler. It prints a clear message
    such as "Line 7: invalid instruction" and carries on, so you see every
    mistake in one run. No .hack file is written if there was any error.
"""

import re
import sys

# --------------------------------------------------------------------------
# Tables
# --------------------------------------------------------------------------

# comp field: 'a' bit + 6 control bits (a c1 c2 c3 c4 c5 c6)
COMP = {
    "0":   "0101010",
    "1":   "0111111",
    "-1":  "0111010",
    "D":   "0001100",
    "A":   "0110000",
    "!D":  "0001101",
    "!A":  "0110001",
    "-D":  "0001111",
    "-A":  "0110011",
    "D+1": "0011111",
    "A+1": "0110111",
    "D-1": "0001110",
    "A-1": "0110010",
    "D+A": "0000010",
    "D-A": "0010011",
    "A-D": "0000111",
    "D&A": "0000000",
    "D|A": "0010101",
    "M":   "1110000",
    "!M":  "1110001",
    "-M":  "1110011",
    "M+1": "1110111",
    "M-1": "1110010",
    "D+M": "1000010",
    "D-M": "1010011",
    "M-D": "1000111",
    "D&M": "1000000",
    "D|M": "1010101",
}
# a few commutative spellings are also accepted (same bits)
for _alt, _std in (("A+D", "D+A"), ("M+D", "D+M"), ("A&D", "D&A"),
                   ("M&D", "D&M"), ("A|D", "D|A"), ("M|D", "D|M")):
    COMP[_alt] = COMP[_std]

JUMP = {
    "":    "000",
    "JGT": "001",
    "JEQ": "010",
    "JGE": "011",
    "JLT": "100",
    "JNE": "101",
    "JLE": "110",
    "JMP": "111",
}

PREDEFINED = {
    "SP": 0, "LCL": 1, "ARG": 2, "THIS": 3, "THAT": 4,
    "SCREEN": 16384, "KBD": 24576,
}
PREDEFINED.update({f"R{i}": i for i in range(16)})

SYMBOL_RE = re.compile(r"^[A-Za-z_.$:][A-Za-z0-9_.$:]*$")
MAX_VALUE = 32767          # largest number an A-instruction can hold (15 bits)


class AsmError(Exception):
    """A problem with one source line (message has no line number)."""


# --------------------------------------------------------------------------
# Translating single instructions
# --------------------------------------------------------------------------

def dest_bits(dest):
    """'D', 'AM', 'MD', ... -> 3 bits in the order A D M."""
    if dest == "":
        return "000"
    if not set(dest) <= set("ADM") or len(set(dest)) != len(dest):
        raise AsmError(f"invalid destination '{dest}'")
    return "".join("1" if ch in dest else "0" for ch in "ADM")


def translate_c(text):
    """Translate  dest=comp;jump  into 16 bits."""
    dest, comp, jump = "", text, ""
    if "=" in comp:
        dest, comp = comp.split("=", 1)
    if ";" in comp:
        comp, jump = comp.split(";", 1)

    if comp not in COMP:
        if comp == "":
            raise AsmError("invalid instruction (missing computation)")
        raise AsmError(f"invalid instruction (unknown computation '{comp}')")
    if jump not in JUMP:
        raise AsmError(f"invalid jump '{jump}'")
    return "111" + COMP[comp] + dest_bits(dest) + JUMP[jump]


# --------------------------------------------------------------------------
# The assembler
# --------------------------------------------------------------------------

def clean(line):
    """Remove comments and every kind of whitespace."""
    return re.sub(r"\s+", "", line.split("//", 1)[0])


def assemble(source_lines):
    """Return (list_of_16_bit_strings, list_of_error_strings)."""
    errors = []
    symbols = dict(PREDEFINED)
    program = []                       # (line_number, text) for real instructions

    # ---------------- first reading: labels ----------------
    for number, raw in enumerate(source_lines, start=1):
        text = clean(raw)
        if not text:
            continue
        if text.startswith("("):
            if not text.endswith(")") or text.count("(") != 1 or text.count(")") != 1:
                errors.append((number, "invalid label (needs the form (NAME))"))
                continue
            name = text[1:-1]
            if not SYMBOL_RE.match(name):
                errors.append((number, f"invalid label name '{name}'"))
            elif name in symbols:
                errors.append((number, f"label '{name}' is already defined"))
            else:
                symbols[name] = len(program)      # address of the NEXT instruction
            continue
        program.append((number, text))

    # ---------------- second reading: translate ----------------
    next_variable = 16
    output = []
    for number, text in program:
        try:
            if text.startswith("@"):
                value = text[1:]
                if value == "":
                    raise AsmError("invalid instruction (nothing after '@')")
                if value.isdigit():
                    number_value = int(value)
                    if number_value > MAX_VALUE:
                        raise AsmError(f"value {number_value} is too big "
                                       f"(maximum is {MAX_VALUE})")
                elif SYMBOL_RE.match(value):
                    if value not in symbols:         # new variable
                        symbols[value] = next_variable
                        next_variable += 1
                    number_value = symbols[value]
                else:
                    raise AsmError(f"invalid symbol or number '{value}'")
                output.append(format(number_value, "016b"))
            else:
                output.append(translate_c(text))
        except AsmError as problem:
            errors.append((number, str(problem)))

    errors.sort(key=lambda item: item[0])
    return output, [f"Line {n}: {msg}" for n, msg in errors]


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 1
    source_path = argv[1]
    if "-o" in argv:
        out_path = argv[argv.index("-o") + 1]
    else:
        out_path = re.sub(r"\.asm$", "", source_path) + ".hack"

    try:
        with open(source_path) as handle:
            lines = handle.read().splitlines()
    except OSError as problem:
        print(f"Cannot read {source_path}: {problem.strerror}")
        return 1

    binary, errors = assemble(lines)
    if errors:
        for message in errors:
            print(message)
        print(f"{len(errors)} error(s) found in {source_path}; no .hack file written.")
        return 1

    with open(out_path, "w") as handle:
        handle.write("\n".join(binary) + "\n")
    print(f"Wrote {len(binary)} instructions to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
