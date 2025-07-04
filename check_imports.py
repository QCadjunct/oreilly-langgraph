# Create a script to check for missing imports
# Save this as check_imports.py and run it

import ast
import importlib
import os
import sys


def find_imports_in_files(directory="."):
    imports = set()
    for root, dirs, files in os.walk(directory):
        # Skip .venv and other common directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        tree = ast.parse(f.read(), filename=filepath)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                imports.add(alias.name.split('.')[0])
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                imports.add(node.module.split('.')[0])
                except Exception as e:
                    print(f"Error parsing {filepath}: {e}")
    
    return imports

def check_missing_imports():
    print("Checking for missing imports in your code...")
    imports = find_imports_in_files()
    missing = []
    
    # Filter out built-in modules
    builtin_modules = set(sys.builtin_module_names)
    
    for imp in sorted(imports):
        if imp in builtin_modules:
            continue
            
        try:
            importlib.import_module(imp)
        except ImportError:
            missing.append(imp)
    
    if missing:
        print("\nMissing packages that need to be installed:")
        for pkg in missing:
            print(f"  - {pkg}")
        print(f"\nTo install missing packages:")
        print(f"uv add {' '.join(missing)}")
    else:
        print("\nAll imports are available!")
    
    return missing

if __name__ == "__main__":
    check_missing_imports()    check_missing_imports()    check_missing_imports()    check_missing_imports()