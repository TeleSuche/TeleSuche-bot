from pathlib import Path
import re

REPLACEMENTS = {
    r'logger\.': 'import logging\nlogger = logging.getLogger(__name__)\n',
    r'LabeledPrice\(': 'from telegram import LabeledPrice\n',
    r'datetime\.now\(\)': 'from datetime import datetime\n'
}

def fix_file(filepath):
    try:
        with open(filepath, 'r+', encoding='utf-8') as f:
            content = f.read()
            needs_import = ""
            
            for pattern, imp in REPLACEMENTS.items():
                if re.search(pattern, content) and imp not in content:
                    needs_import += imp
            
            if needs_import:
                content = needs_import + content
                f.seek(0)
                f.write(content)
                f.truncate()
                print(f"Import ajouté dans {filepath}")
    except Exception as e:
        print(f"Erreur sur {filepath}: {str(e)}")

def main():
    project_root = Path(__file__).parent
    for py_file in project_root.rglob('*.py'):
        fix_file(py_file)

if __name__ == "__main__":
    main()
