#!/usr/bin/env python3
from sys import argv


if __name__ == "__main__":
    if "--help" in argv or "-h" in argv:
        print(
            """
Usage:  ./pandemonium
        ./pandemonium (--server | -s)
        ./pandemonium (--help | -h)
        ./pandemonium [--no-fullscreen | --no-vsync | --no-multiplayer]
"""
        )
    elif "--server" in argv or "-s" in argv:
        import server.server
    else:
        from client.client import *


        main(multiplayer=not "--no-multiplayer" in argv)
        # import cProfile; cProfile.run('main(multiplayer=not "--no-multiplayer" in argv)')

