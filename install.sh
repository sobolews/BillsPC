#!/bin/bash
set -ev
pip install -r requirements.txt
git submodule update --init
(cd showdowndata/Pokemon-Showdown && npm install --production)
cp showdowndata/js/* showdowndata/Pokemon-Showdown
cp showdowndata/Pokemon-Showdown/config/config-example.js showdowndata/Pokemon-Showdown/config/config.js
echo "Dependencies installed. Run ./test.sh to test"
