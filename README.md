[![Build Status](https://travis-ci.org/sobolews/BillsPC.svg?branch=master)](https://travis-ci.org/sobolews/BillsPC)
## Bill's PC
Bill's PC is an AI project, intended for playing [Pokemon Showdown](http://pokemonshowdown.com/)'s Random Battle format.

#### Installation
Bill's PC is developed on Ubuntu 14.04 and untested on other systems. If python and the other dependencies are supported, then it will probably run.

Pre-installation dependencies:
* python2.7
* pip
* nodejs
* npm
* git 1.7.2+

```
git clone https://github.com/sobolews/BillsPC.git
cd BillsPC
```
Optional (but recommended): use a virtualenv!
>```
sudo pip install virtualenv virtualenvwrapper
source /usr/local/bin/virtualenvwrapper.sh
mkvirtualenv -a . -p /usr/bin/python2.7 BillsPC
```

```
./install.sh
./test.sh
```
--- 
Bill's PC is currently in development!
##### Development schedule (by priority)

| Item                                                | Status |    |
| ---                                                 |:------:| ---|
| make a showdown pokedex data miner                  | done | :white_check_mark: 
| make a randombattle statistics miner                | done | :white_check_mark: 
| create battle engine logic and base data structures | done | :white_check_mark: 
| implement moves                                     | done | :white_check_mark: 
| implement abilities                                 | done | :white_check_mark: 
| implement items                                     | done | :white_check_mark:
| implement mega evolution                            | done | :white_check_mark:
| implement forme changes                             | done | :white_check_mark:
| implement a Showdown battle client/bot              | done | :white_check_mark: 
| implement AI (using [Simultaneous-Move](http://mlanctot.info/files/papers/cig14-smmctsggp.pdf) [Monte Carlo Tree Search](http://pubs.doc.ic.ac.uk/survey-mcts-methods/survey-mcts-methods.pdf) for stacked matrix games and/or LP solutions for Nash equilibria with learned valuation functions) | in progress | :large_blue_diamond:
| implement remaining non-randbats moves/abilities/items | maybe | :interrobang:
| Update for Gen 7 - November 2016                    | to do | :white_medium_square:

#### Notes

Bill's PC is largely still just a prototype, and I am fully expecting to have to
rewrite it in C++ to gain enough performance for AI algorithms to be
successful. Currently, I only plan to implement moves, items, and abilities that
appear in Showdown's randbats (random battle) format, and have the bot exploit
statistics gained from offline team generation using Showdown's algorithm. As
Showdown changes their random movesets, I will try to update Bill's PC with any
new mechanics that need to be implemented.
