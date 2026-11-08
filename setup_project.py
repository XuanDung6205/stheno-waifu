
from pathlib import Path

ROOT = Path(__file__).resolve().parent

directories = [
    "src/core",
    "src/brain",
    "src/personality",
    "src/emotion",
    "src/memory",
    "src/voice",
    "src/interface",
    "config",
    "data",
    "tests",
    "scripts",
    "docs",
]

files = [
    "src/__init__.py",
    "src/main.py",
    "src/core/__init__.py",
    "src/brain/__init__.py",
    "src/personality/__init__.py",
    "src/emotion/__init__.py",
    "src/memory/__init__.py",
    "src/voice/__init__.py",
    "src/interface/__init__.py",
    "config/settings.json",
    "tests/__init__.py",
    "scripts/__init__.py",
    "requirements.txt",
    ".env",
    ".env.example",
    ".gitignore",
    "README.md",
]

for directory in directories:
    (ROOT / directory).mkdir(parents=True, exist_ok=True)

for filename in files:
    path = ROOT / filename
    path.parent.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        path.touch()

print("=== STHENO PROJECT CREATED ===")

for path in sorted(ROOT.rglob("*")):
    if ".venv" in path.parts or "__pycache__" in path.parts:
        continue

    relative = path.relative_to(ROOT)
    depth = len(relative.parts) - 1
    prefix = "    " * depth
    symbol = "[DIR]" if path.is_dir() else "[FILE]"

    print(f"{prefix}{symbol} {path.name}")
