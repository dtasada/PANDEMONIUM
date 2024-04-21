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
        ./pandemonium -fm   --   Example: run without fullscreen or multiplayer
"""
        )
    elif "--server" in argv or "-s" in argv:
        import server.server
    else:
        from client.client import *

        main(
            multiplayer=not any(
                x in argv for x in ("--no-multiplayer", "-m", "-fm", "-mf")
            )
        )
        # import cProfile; cProfile.run('main(multiplayer=not "--no-multiplayer" in argv)')
