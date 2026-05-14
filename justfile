# vx-registro-de-uso

# Bump version in pyproject.toml, commit, tag, and push — triggers the GitHub Actions release
release version:
    #!/usr/bin/env bash
    set -euo pipefail
    CURRENT=$(just version)
    echo "📦 Bump: v${CURRENT} → v{{version}}"
    sed -i.bak -E 's/^version = "'"${CURRENT}"'"/version = "{{version}}"/' pyproject.toml
    rm -f pyproject.toml.bak
    git add pyproject.toml
    git commit -m "Bump version to v{{version}}"
    git tag "v{{version}}"
    git push --atomic origin HEAD "v{{version}}"
    echo "✅ v{{version}} pushed — GitHub Actions will build the image and release"

# Show the current version
version:
    @grep -m1 '^version' pyproject.toml | sed -E 's/.*"([^"]+)".*/\1/'
