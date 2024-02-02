from sys import argv
from base64 import b64decode
from functions_map import fm
from phplint import php_lint

if len(argv) < 2:
    print("Usage: %s <file.php>" % (argv[0]))
    exit(-1)

file = argv[1]

def apply_fm(code, fm):
    for func in fm:
        func_readable = fm[func]
        if func_readable == func:
            continue
        print(f"[function map] {func.__repr__()} -> {func_readable.__repr__()}")
        code = code.replace(func, func_readable)
    return code

base64_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

def find_and_after(s,what):
    y = s.find(what)
    if y < 0:
        return s
    return s[y+len(what):]

def find_and_before(s,what):
    y = s.find(what)
    if y < 0:
        return s
    return s[:y]

with open(file, "r") as f:
    print(f"Decompiling {file}...")
    text = f.read()
    data = find_and_before(find_and_after(text, "/*"), "*/")
    skip = len("CNS")+6 # CNSnnnnnn (n = number)

    base64_translator_offset = skip
    base64_translator_len = 52

    base64_offset = base64_translator_offset + base64_translator_len

    b64translator = data[base64_translator_offset:][:base64_translator_len]
    code = data[base64_offset:]
    with open(file+".DECOMPILED.php", "w+") as f:
        try:
            #add "<?php" because cncrypto use "eval"
            code = "<?php \n" + b64decode(code.translate(str.maketrans(base64_chars, b64translator))).decode()
        except:
            code = text

        try:
            print("Linting...")
            code = php_lint(code, verbose=False)
        except Exception:
                pass

        print("[WARN] function map is only changing function names while linting :(")
        apply_fm(code, fm)

        f.write(code)
print("Done!")