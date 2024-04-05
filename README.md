# PANDEMONIUM

* Trello available at [https://trello.com/b/FjleDUU4/pandemonium](https://trello.com/b/FjleDUU4/pandemonium)

## Requirements
* Run `pip install -r requirements.txt` to install `pygame-ce==2.4.0` (or other libraries we might add later)

## How to run
* Run `./pandemonium.py`. By default it will search for a server, but you can disable online & multiplayer behavior with `--no-multiplayer`.
* To run the server, run `./pandemonium.py --server`.
* `--no-fullscreen` and `--no-vsync` are also available for testing purposes, but are not recommended for gameplay.

## Todo
### Bugs
* FLOOR AND CEILING TEXTURES
* Fix ADS with single ray
* Fix enemy height
* Fix fisheye bug
* Fix mouse flickering
* Fix shooting through walls

### Features
* Leaderboard & Point system
* Enemy direction and sounds (including shots & footsteps)
