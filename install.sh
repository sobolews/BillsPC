#!/bin/bash
set -ev
pip install -r requirements.txt
git submodule update --init
(cd mining/Pokemon-Showdown && npm install --production)
cp mining/js/* mining/Pokemon-Showdown
echo "Dependencies installed. Run ./test.sh to test"
