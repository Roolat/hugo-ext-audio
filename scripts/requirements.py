# Extracting dependencies from lock file.
# LGTM looks for setup.py or requirements.txt files, but fails.
# We are using Poetry, which has no feature to export dependencies list yet...
# Should be started from the project root.

LOCK_FILE = "pyproject.lock"
REQUIREMENTS_FILE = "requirements.txt"

if __name__ == "__main__":
    import tomlkit

    lockfile = tomlkit.parse(open(LOCK_FILE).read())
    depsfile = open(REQUIREMENTS_FILE, "w")

    deps = []

    for dep in lockfile["package"]:
        if dep["category"] == "main":
            if "source" not in dep:
                deps.append(
                    "{name}=={version}".format(
                        name=dep["name"], version=dep["version"]
                    )
                )
            else:
                if dep["source"]["type"] == "git":
                    deps.append(
                        "git+{url}@{ref}".format(
                            url=dep["source"]["url"],
                            ref=dep["source"]["reference"],
                        )
                    )
                else:
                    raise ValueError(
                        "Unknown source type for {}".format(dep["name"])
                    )

    depsfile.write("\n".join(deps))
    depsfile.close()
