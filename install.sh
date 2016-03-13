#!/bin/bash
set -ev
pip install -r requirements.txt
git submodule update --init
(cd mining/Pokemon-Showdown && npm install --production)
cp mining/js/* mining/Pokemon-Showdown
cp mining/Pokemon-Showdown/config/config-example.js mining/Pokemon-Showdown/config/config.js
echo "Dependencies installed. Run ./test.sh to test"
