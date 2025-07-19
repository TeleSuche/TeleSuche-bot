import re
from pathlib import Path

def fix_imports(content):
    """Corrige les problèmes d'import dans le code"""
    # Corriger les imports sur une seule ligne
    content = re.sub(r'from (\w+) import (.+?) from', r'from \1 import \2\nfrom', content)
    content = re.sub(r'import (\w+), (\w+) from', r'import \1\nimport \2 from', content)
    return content

def process_file(filepath):
    """Traite un fichier pour corriger ses imports"""
    try:
        with open(filepath, 'r+', encoding='utf-8') as f:
            content = f.read()
            fixed = fix_imports(content)
            if fixed != content:
                f.seek(0)
                f.write(fixed)
                f.truncate()
                print(f"Corrigé : {filepath}")
    except Exception as e:
        print(f"Erreur sur {filepath}: {str(e)}")

def main():
    """Fonction principale du script"""
    project_root = Path(__file__).parent
    for py_file in project_root.rglob('*.py'):
        process_file(py_file)

if __name__ == "__main__":
    main()