#!/bin/bash
set -x
pylint --rcfile=./pylintrc $(cat <(find . -mindepth 1 -maxdepth 1 -type d ! -name .git ! -name tests) <(git ls-tree --name-only HEAD | grep '\w\+.py'))
