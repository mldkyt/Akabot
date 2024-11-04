import os
import re

def get_files(path: str) -> list[str]:
    # Get list of .py files, recursively in directories

    files = []
    for root, _, filenames in os.walk(path):
        for filename in filenames:
            if filename.endswith('.py'):
                files.append(os.path.join(root, filename))

    return files


if __name__ == '__main__':

    files = get_files("../")

    for i in files:
        with open(i) as f:
            script = f.read()

        for j in re.findall(r"get_key\(['\"]([a-zA-Z_]+)['\"](, ['\"]true['\"])?\)", script):
            print(j[0].upper())
