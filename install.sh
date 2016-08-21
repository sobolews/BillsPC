#!/bin/bash
set -ex
pip install -r requirements.txt
git submodule update --init
(cd showdowndata/Pokemon-Showdown && npm install --production)
cp showdowndata/js/* showdowndata/Pokemon-Showdown
cp showdowndata/Pokemon-Showdown/config/config-example.js showdowndata/Pokemon-Showdown/config/config.js
(set +x; echo 'Dependencies installed.' \
              'Generating randbats statistics file (rbstats.pkl) with 5000 teams.' \
              'For better results, you should mine for at least 100,000 teams with' \
              '`./BillsPC.py mine 100000`') 2>/dev/null
./BillsPC.py mine 5000
(set +x; echo 'Done. Run `./test.sh` to test') 2>/dev/null
