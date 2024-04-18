#!/usr/bin/env python3
from random import randint, choice
from threading import Thread
from typing import Any, Dict, Optional
import atexit
import json
import socket
import sys


class Colors:
    GREEN = "\033[1;32m"
    RED = "\033[1;31;31m"
    RESET = "\033[0m"


SERVER_ADDRESS, SERVER_TCP_PORT, SERVER_UDP_PORT = (
    socket.gethostbyname(socket.gethostname()),
    6969,
    4200,
)


def alert(*msg):
    print(Colors.RED + msg[0] + Colors.RESET + ":", msg[1])


try:
    server_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_udp.bind((SERVER_ADDRESS, SERVER_UDP_PORT))
    print(
        f"{Colors.GREEN}UDP server is listening at {SERVER_ADDRESS}:{SERVER_UDP_PORT}{Colors.RESET}"
    )
except BaseException as e:
    sys.exit(f"{Colors.RED}UDP server failed to initialize: {Colors.RESET}{e}")


try:
    server_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_tcp.bind((SERVER_ADDRESS, SERVER_TCP_PORT))
    server_tcp.listen()
    print(
        f"{Colors.GREEN}TCP server is listening at {SERVER_ADDRESS}:{SERVER_TCP_PORT}{Colors.RESET}"
    )
except BaseException as e:
    sys.exit(f"{Colors.RED}TCP server failed to initialize: {Colors.RESET}{e}")


tcp_data: Dict[str, dict[str, Any]] = {}  # values are health, color and name
udp_data: Dict[str, dict[str, Any]] = {}  # values are x, y, angle
clients: list[socket.socket] = []
inactive_clients: list[socket.socket] = []
inactive_data: Dict[str, dict[str, Any]] = {}


def feed(msg: str) -> None:
    for client in clients.copy():
        client.send(f"feed|{msg}\n".encode())


def off(opt: str, target: str, args: list[str], killer: Optional[str] = None):
    try:
        # Fix this: It raises an exception but has no perceivable bug or error,
        # but that might be shitty in the future
        name = tcp_data[target]["name"]
        messages = {
            "kill": [
                f"imagine being {name} rn",
                f"{name} got PANDEMONIUMED",
                f"{name} got shit on",
                f"{name} was neutralized",
                f"{name} was neutered :(",
                f"{name} was offed",
                f"{name} :skull:",
            ],
            "quit": [
                f"{name} doesn't wanna play anymore",
                f"{name} has better things to do",
                f"{name} left",
                f"{name} quit",
                f"{name} rage quit",
            ],
        }
        feed(messages[opt][randint(0, len(messages[opt]) - 1)])

        saved_data = udp_data[target]
        del udp_data[target]
        del tcp_data[target]

        for client_ in clients.copy():
            if client_ != client:
                client_.send(f"{opt}|{target}\n".encode())

            if str(client_.getpeername()) == target:
                clients.remove(client_)
                # if not F4ing, move client from clients to inactive, otherwise, completely remove
                if (opt == "quit" and "f4" not in args) or (opt == "kill"):
                    inactive_clients.append(client_)
                    inactive_data[target] = {
                        "deaths": saved_data["deaths"],
                        "kills": saved_data["kills"],
                        "score": saved_data["score"],
                    }

    except BaseException as e:
        alert(f"Failed to {opt} player", e)


def receive_udp():
    while True:
        request, addr = server_udp.recvfrom(2**12)
        request = json.loads(request)
        udp_data[request["tcp_id"]].update(request["body"])
        udp_data[request["tcp_id"]][
            "udp_id"
        ] = addr  # careful, this is a tuple, not a string
        for v in udp_data.values():
            server_udp.sendto(json.dumps(udp_data).encode(), v["udp_id"])


def receive_tcp(client: socket.socket, client_addr):
    try:
        while True:
            raw = client.recv(2**12)
            msg = raw.decode().strip()
            request = msg.split("|")
            verb = request[0]  # verb like "kill"
            target = request[1]  # target is a tcp id (`request[1]` is a string)

            args = []  # every item after the target is an arg, like a damage coef
            if len(request) >= 3:
                args = request[2:]
            try:
                match verb:
                    case "init_player":
                        try:
                            client.send(
                                ("init_res|" + json.dumps(tcp_data) + "\n").encode()
                            )
                            tcp_data[str(client_addr)] = json.loads(args[0])
                            udp_data[str(client_addr)] = {
                                "kills": 0,
                                "deaths": 0,
                                "score": 500,
                            }

                            # Introduce to all other players
                            for client_ in clients.copy():
                                if client_ != client:
                                    client_.send((msg + "\n").encode())

                            for client_ in inactive_clients.copy():
                                if client.getpeername() == client_.getpeername():
                                    id_ = str(client_.getpeername())

                                    inactive_clients.remove(client_)
                                    clients.append(client_)
                                    udp_data[id_] = inactive_data[id_]
                                    del inactive_data[id_]

                            name = tcp_data[str(client_addr)]["name"]
                            messages = [
                                f"say hi to {name}!",
                                f"{name} also wants to play",
                                f"{name} hails!",
                                f"{name} joined",
                                f"Have much fear, {name} is here!",
                            ]
                            feed(choice(messages))

                        except BaseException as e:
                            alert("Could not init_player", e)

                    case "quit":
                        off("quit", target, args)
                    case "kill":
                        off("kill", target, args, str(client.getpeername()))

                    case "inc_score":
                        udp_data[target]["score"] += int(args[0])
                        for client_ in clients:
                            if str(client_.getpeername()) == target:
                                client_.send(f"inc_score|{args[0]}\n".encode())

                    case "shoot":
                        for client_ in clients.copy():
                            if client_ != client:
                                client_.send((msg + "\n").encode())

                    case "damage":
                        try:
                            tcp_data[target]["health"] = max(
                                tcp_data[target]["health"] - int(args[0]), 0
                            )

                            if tcp_data[target]["health"] <= 0:
                                udp_data[target]["deaths"] += 1
                                udp_data[str(client_addr)]["kills"] += 1
                                # Rest of death handling is done elsewhere

                            for client_ in clients.copy():
                                if target == str(client_.getpeername()):
                                    client_.send(
                                        f"take_damage|{client_addr}|{args[0]}\n".encode()
                                    )

                        except BaseException as e:
                            alert("Failed to damage player", e)

            except BaseException as e:
                alert("Error sending TCP message", e)

    except BaseException as e:
        print(f"Could not handle client {client_addr}", e)

    client.close()
    print(f"Closed connection with {client_addr}")


# UDP
Thread(target=receive_udp, daemon=True).start()


def quit():
    [client.close() for client in clients.copy()]

    server_tcp.close()
    server_udp.close()

    print("Exited successfully")


atexit.register(quit)

while True:
    # TCP
    try:
        client, client_addr = server_tcp.accept()
        clients.append(client)
        print(f"New connection from {client_addr}")
        Thread(
            target=receive_tcp,
            args=(client, client_addr),
            daemon=True,
        ).start()

    except ConnectionAbortedError:
        print(f"{Colors.RED}Connection aborted!{Colors.RESET}")

    except KeyboardInterrupt:
        break
