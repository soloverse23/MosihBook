#!/bin/bash
export PYTHONUTF8=1
"$HOME/Library/Application Support/MosiBooks/venv/bin/python" -m bookforge.cli claude-login
read -r -p "Press Enter to close."
