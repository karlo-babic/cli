#!/usr/bin/env python3
"""
_check: Verify that all scripts and the launcher follow SPEC (dev tool, not served as a script).
Usage: python3 _check.py
"""

import os
import re
import sys
import ast

# -- fmt ---------------------------------------------------------------------
import os as _os; _e = _os.environ
_C = "NO_COLOR" not in _e and bool(_e.get("FORCE_COLOR")=="1" or _e.get("WT_SESSION") or _e.get("ANSICON") or _e.get("TERM_PROGRAM") or _e.get("TERM","") not in ("","dumb"))
def section(t): print(f"\n\033[36m=== {t} ===\033[0m" if _C else f"\n=== {t} ===")
def info(m):    print(f"\033[90m[*]\033[0m {m}"       if _C else f"[*] {m}")
def ok(m):      print(f"\033[32m[+]\033[0m {m}"       if _C else f"[+] {m}")
def err(m):     print(f"\033[31m[-]\033[0m {m}"       if _C else f"[-] {m}")
def warn(m):    print(f"\033[33m[!]\033[0m {m}"       if _C else f"[!] {m}")
# -----------------------------------------------------------------------------

ROOT = os.path.dirname(os.path.abspath(__file__))
SHEBANG = "#!/usr/bin/env python3"


def read(name):
    with open(os.path.join(ROOT, name), "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def find_scripts():
    """Scripts are extensionless files whose first line is the python3 shebang."""
    scripts = []
    for name in sorted(os.listdir(ROOT)):
        path = os.path.join(ROOT, name)
        if not os.path.isfile(path) or os.path.splitext(name)[1]:
            continue
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            if f.readline().rstrip("\n") == SHEBANG:
                scripts.append(name)
    return scripts


def spec_fmt_block():
    """The fmt block as written in SPEC (indented by 4 spaces there)."""
    lines, inside = [], False
    for line in read("SPEC").splitlines():
        if line.strip().startswith("# -- fmt"):
            inside = True
        if inside:
            lines.append(line[4:])
            if line.strip().startswith("# ----"):
                break
    return "\n".join(lines) + "\n"


def runner_source():
    """The Python code embedded in index.html (between the shebang and '# -->')."""
    html = read("index.html")
    start = html.index(SHEBANG)
    end = html.rindex("# -->")
    return html[start:end]


def load_scripts_dict(runner_src):
    """Evaluate the SCRIPTS dict from the launcher source (BASE_URL resolved)."""
    tree = ast.parse(runner_src)
    env = {"__builtins__": {}, "True": True, "False": False}
    scripts_node = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id == "BASE_URL":
                env["BASE_URL"] = ast.literal_eval(node.value)
            elif node.targets[0].id == "SCRIPTS":
                scripts_node = node.value
    expr = ast.Expression(scripts_node)
    return env["BASE_URL"], eval(compile(expr, "SCRIPTS", "eval"), env)


def docstring_usage(src):
    """(first docstring line, Usage text) from a script's raw source."""
    parts = src.split('"""')
    if len(parts) < 3:
        return None, None
    doc = parts[1].strip("\n")
    first = doc.splitlines()[0] if doc else ""
    idx = doc.find("Usage: ")
    usage = doc[idx + len("Usage: "):].rstrip() if idx >= 0 else None
    return first, usage


def module_level_imports(tree):
    """Top-level module names imported outside functions/classes."""
    names = []
    def visit(nodes):
        for node in nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if isinstance(node, ast.Import):
                names.extend(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names.append(node.module.split(".")[0])
            for field in ("body", "orelse", "finalbody", "handlers"):
                visit(getattr(node, field, []) or [])
    visit(tree.body)
    return names


def main():
    section("SPEC Check")
    problems = []

    def check(title, failures):
        if failures:
            for f in failures:
                err(f"{title}: {f}")
            problems.extend(failures)
        else:
            ok(title)

    scripts = find_scripts()
    info(f"Found {len(scripts)} scripts: {', '.join(scripts)}")
    sources = {name: read(name) for name in scripts}
    runner = runner_source()

    # 1. fmt block
    fmt = spec_fmt_block()
    check("fmt block identical to SPEC",
          [name for name, src in list(sources.items()) + [("index.html", runner)] if fmt not in src])

    # 2. ASCII only
    non_ascii = []
    for name in scripts + ["index.html", "SPEC", os.path.basename(__file__)]:
        for lineno, line in enumerate(read(name).splitlines(), 1):
            if any(ord(c) > 127 for c in line):
                non_ascii.append(f"{name}:{lineno}")
    check("ASCII only", non_ascii)

    # 3. Docstring
    doc_failures, usages = [], {}
    for name, src in sources.items():
        first, usage = docstring_usage(src)
        if not first or not re.match(r"^\S+: \S", first):
            doc_failures.append(f"{name} (missing 'Name: description' line)")
        if usage is None:
            doc_failures.append(f"{name} (missing 'Usage:' line)")
        elif not usage.startswith(name):
            doc_failures.append(f"{name} (Usage must start with the bare script name)")
        usages[name] = usage
    check("Docstring has description and Usage line", doc_failures)

    # 4. Registration in index.html
    try:
        base_url, registry = load_scripts_dict(runner)
    except Exception as e:
        err(f"Could not read SCRIPTS from index.html: {e}")
        print()
        sys.exit(1)
    reg_failures = []
    for name in scripts:
        if name not in registry:
            reg_failures.append(f"{name} (not in SCRIPTS)")
    for name, entry in registry.items():
        if name not in scripts:
            reg_failures.append(f"{name} (in SCRIPTS but no such script file)")
            continue
        if entry.get("url") != base_url + name:
            reg_failures.append(f"{name} (url is not BASE_URL + name)")
        if entry.get("usage") != usages.get(name):
            reg_failures.append(f"{name} (usage differs from docstring)")
        desc = entry.get("description", "")
        if not desc or desc.endswith("."):
            reg_failures.append(f"{name} (description missing or ends with a period)")
    check("Registered in index.html SCRIPTS", reg_failures)

    # 5. Compiles (in memory, no __pycache__)
    trees, compile_failures = {}, []
    for name, src in list(sources.items()) + [("index.html", runner)]:
        try:
            trees[name] = ast.parse(src, filename=name)
            compile(trees[name], name, "exec")
        except SyntaxError as e:
            compile_failures.append(f"{name}:{e.lineno} {e.msg}")
    check("Compiles", compile_failures)

    # 6. Stdlib only at module level
    stdlib = getattr(sys, "stdlib_module_names", None)
    if stdlib is None:
        warn("Stdlib import check skipped (needs Python 3.10+)")
    else:
        check("Module-level imports are stdlib only",
              [f"{name} imports '{mod}'" for name, tree in trees.items()
               for mod in module_level_imports(tree) if mod not in stdlib])

    if problems:
        err(f"{len(problems)} problem{'s' if len(problems) != 1 else ''} found")
        print()
        sys.exit(1)
    ok("All checks passed")
    print()


if __name__ == "__main__":
    main()
