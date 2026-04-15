#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (two levels up from the script)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Change to project root directory
cd "$PROJECT_ROOT"

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Created .env from .env.example"
else
    echo ".env already exists; leaving existing file unchanged"
fi

python3 - <<PY
from pathlib import Path

project_root = Path(r"$PROJECT_ROOT")
env_path = project_root / ".env"
lines = env_path.read_text().splitlines()
updated = False
new_lines = []

for line in lines:
    if line.startswith("ROOT="):
        new_lines.append(f"ROOT={project_root}")
        updated = True
    else:
        new_lines.append(line)

if not updated:
    if new_lines and new_lines[-1].strip() != "":
        new_lines.append("")
    new_lines.append(f"ROOT={project_root}")

env_path.write_text("\n".join(new_lines) + "\n")
print(f"Set ROOT in {env_path}")
PY

echo "Please open .env and fill in any placeholder credentials before running credentialed steps."
