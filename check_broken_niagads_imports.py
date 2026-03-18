import ast
import os
import importlib.util

# poetry run python check_broken_niagads_imports.py


def find_py_files(root):
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            if filename.endswith(".py"):
                yield os.path.join(dirpath, filename)


def check_import(module):
    try:
        return importlib.util.find_spec(module) is not None
    except Exception:
        return False


def run(root="."):
    print(f"Processing {root}")
    broken = []
    for filepath in find_py_files(root):
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            try:
                tree = ast.parse(f.read(), filename=filepath)
            except Exception:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("niagads"):
                            if not check_import(alias.name):
                                broken.append((filepath, alias.name))
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.startswith("niagads"):
                        mod = node.module
                        if not check_import(mod):
                            broken.append((filepath, mod))
    if broken:
        print("Broken niagads imports found:")
        for path, mod in broken:
            print(f"{path}: {mod}")
    else:
        print("No broken niagads imports found.")


if __name__ == "__main__":
    for subdir in ["components", "bases", "projects", "development"]:
        if os.path.isdir(subdir):
            run(root=subdir)
