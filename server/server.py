#!/usr/bin/env python3
from random import randint
from threading import Thread
from typing import Any, Dict
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
    server_tcp.listen(10)
    print(
        f"{Colors.GREEN}TCP server is listening at {SERVER_ADDRESS}:{SERVER_TCP_PORT}{Colors.RESET}"
    )
except BaseException as e:
    sys.exit(f"{Colors.RED}TCP server failed to initialize: {Colors.RESET}{e}")


tcp_data: Dict[str, dict[str, Any]] = {}  # values are health, color and name
udp_data: Dict[str, dict[str, Any]] = {}  # values are x, y, angle
clients: list[socket.socket] = []
inactive_clients: list[socket.socket] = []


def feed(msg: str) -> None:
    for client in clients.copy():
        client.send(f"feed|{msg}\n".encode())


def off(target: str, opt: str):
    try:
        name = tcp_data[target]["name"]
        messages = {
            "kill": [
                f"imagine being {name} rn 💀",
                f"{name} got PANDEMONIUMED",
                f"{name} got shit on",
                f"{name} was neutralized",
                f"{name} was offed",
                f"{name} 💀💀",
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

        del udp_data[target]
        del tcp_data[target]

        for client_ in clients.copy():
            if client_ != client:
                print(f"sending sig to {opt} {target}")
                client_.send(f"{opt}|{target}\n".encode())

            if str(client_.getpeername()) == target:
                # if not F4ing, move client from clients to inactive_clients, otherwise, completely remove
                clients.remove(client_)
                if (opt == "quit" and not target) or (opt == "kill"):
                    inactive_clients.append(client_)
    except BaseException as e:
        alert(f"Failed to {opt} player", e)


def receive_udp():
    while True:
        request, addr = server_udp.recvfrom(2**12)
        request = json.loads(request)
        udp_data[request["tcp_id"]] = request["body"]
        udp_data[request["tcp_id"]][
            "udp_id"
        ] = addr  # careful, this is a tuple, not a string

        for tcp_id, content in udp_data.copy().items():
            try:
                response = {k: v for k, v in udp_data.copy().items() if k != tcp_id}
                response = json.dumps(response)
                server_udp.sendto(response.encode(), content["udp_id"])
            except:
                pass


def receive_tcp(client: socket.socket, client_addr):
    try:
        while True:
            raw = client.recv(2**12)
            request = raw.decode().split("|")
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

                            # Introduce to all other players
                            for client_ in clients.copy():
                                if client_ != client:
                                    client_.send(raw + b"\n")

                            for client_ in inactive_clients.copy():
                                if client.getpeername() == client_.getpeername():
                                    inactive_clients.remove(client_)
                                    clients.append(client_)

                            print("Initialized player:", tcp_data[str(client_addr)])

                            name = tcp_data[str(client_addr)]["name"]
                            messages = [
                                f"say hi to {name}!",
                                f"{name} also wants to play",
                                f"{name} hails!",
                                f"{name} joined",
                            ]
                            feed(messages[randint(0, len(messages) - 1)])

                        except BaseException as e:
                            alert("Could not init_player", e)

                    case "quit":
                        off(target, "quit")
                    case "kill":
                        off(target, "kill")

                    case "damage":
                        try:
                            tcp_data[target]["health"] = max(
                                tcp_data[target]["health"] - int(args[0]), 0
                            )

                            for client_ in clients.copy():
                                if target == str(client_.getpeername()):
                                    client_.send(f"take_damage|{args[0]}\n".encode())

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
        Thread(target=receive_tcp, args=(client, client_addr), daemon=True).start()

    except ConnectionAbortedError:
        print(f"{Colors.RED}Connection aborted!{Colors.RESET}")

    except KeyboardInterrupt:
        break
