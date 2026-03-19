import importlib.util
import os
import sys

docs = []

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
        split = docs_out.split("\n")
        name = split[0][2:]
        description = split[2]

        with open(f"docs/{name}.md", "w") as f:
            f.write(docs_out)

        docs.append({
            "name": name,
            "description": description
        })
    except Exception as e:
        print(e)

with open("docs/description.md", "w") as f:
    f.write("# Nekona\n\nNekona is a featureful open-source bot and a full rewrite of Akabot!\n\nFeatures:\n")

    for i in docs:
        f.write(f"- {i['name']}: {i['description']}\n")

    f.write("\n"
            "## Support\n\n"
            "- Join the Discord server: https://discord.gg/aE2MXH5Qp6\n"
            "- Read the documentation: https://git.the-wired.club/lain/nekona/wiki\n")

with open("docs/Home.md", "w") as f:
    f.write("# Nekona\n\nNekona is a featureful open-source bot and a full rewrite of Akabot!\n\nFeatures:\n")

    for i in docs:
        f.write(
            f"- [{i['name']}](https://git.the-wired.club/lain/nekona/wiki/{i['name'].replace(' ', '%20')}.md): {i['description']}\n")

    f.write("\n"
            "## Support\n\n"
            "- Join the Discord server: https://discord.gg/aE2MXH5Qp6\n"
            "- Read the documentation: https://git.the-wired.club/lain/nekona/wiki\n")

with open("docs/_Sidebar.md", "w") as f:
    for i in docs:
        f.write(f"* [{i['name']}](https://git.the-wired.club/lain/nekona/wiki/{i['name'].replace(' ', '%20')}.md)\n")
