#!/bin/bash
set -v
pylint --rcfile=./pylintrc $(find . -mindepth 1 -maxdepth 1 -name "*.py" -or -type d ! -name .git ! -name tests)
