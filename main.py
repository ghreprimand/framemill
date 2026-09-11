"""Flet packaging entrypoint.

`flet build` looks for main.py at the repository root. The supported user
command remains `framemill` / `framemill-gui` from the installed package.
"""
from framemill.app import run

if __name__ == "__main__":
    run()
