import importlib.util
import os
import sys

for i in os.listdir("cogs"):
    # We are going to load the files (dangerous!) and run the docs() function, which returns the generated help
    if not i.endswith('.py'):
        continue

    i = i[:-3]

    if not os.path.exists("docs"):
        os.mkdir("docs")

    spec = importlib.util.spec_from_file_location(f"cogs.{i}", f"cogs/{i}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"cogs.{i}"] = mod
    spec.loader.exec_module(mod)

    try:
        docs_out: str = mod.docs()
        name = docs_out.split("\n")[0]

        with open(f"docs/{name}.md", "w") as f:
            f.write(docs_out)
    except Exception as e:
        print(e)
