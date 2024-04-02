#!/usr/bin/env python3
import sys
import socket
import json
from threading import Thread
from typing import Any, Dict


class Colors:
    GREEN = "\033[1;32m"
    RED = "\033[1;31;31m"
    RESET = "\033[0m"


SERVER_ADDRESS, SERVER_TCP_PORT, SERVER_UDP_PORT = (
    socket.gethostbyname(socket.gethostname()),
    6969,
    420,
)


def alert(*msg):
    print(Colors.RED + msg[0] + Colors.RESET + ":", msg[1])


try:
    server_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_udp.bind((SERVER_ADDRESS, SERVER_UDP_PORT))
    print(
        f"{Colors.GREEN}UDP server is listening at {SERVER_ADDRESS}:{SERVER_UDP_PORT}{Colors.RESET}"
    )
except Exception as err:
    sys.exit(f"{Colors.RED}UDP server failed to initialize: {Colors.RESET}{err}")


try:
    server_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_tcp.bind((SERVER_ADDRESS, SERVER_TCP_PORT))
    server_tcp.listen(10)
    print(
        f"{Colors.GREEN}TCP server is listening at {SERVER_ADDRESS}:{SERVER_TCP_PORT}{Colors.RESET}"
    )
except Exception as err:
    sys.exit(f"{Colors.RED}TCP server failed to initialize: {Colors.RESET}{err}")


tcp_data: Dict[str, dict[str, Any]] = {}  # values are health, color and name
udp_data: Dict[str, dict[str, Any]] = {}  # values are x, y, angle
clients: list[socket.socket] = []


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


def receive_tcp(client, client_addr):
    try:
        while True:
            raw = client.recv(2**12)
            request = raw.decode().split("|")
            verb = request[0]  # verb like "kill"
            target = request[1]  # target is a tcp id
            args = []  # every item after the target is an arg, like a damage coef
            if len(request) >= 3:
                args = request[2:]

            try:
                match verb:
                    case "init_player":
                        try:
                            client.send(json.dumps(tcp_data).encode())
                            tcp_data[str(client_addr)] = json.loads(args[0])

                            # Introduce to all players
                            for client_ in clients.copy():
                                client_.send(raw)

                            print("Initialized player:", tcp_data)
                        except BaseException as e:
                            alert("Could not init_player", e)

                    case "quit":
                        del udp_data[str(client_addr)]
                        del tcp_data[str(client_addr)]

                        # TODO: finish quitting

                    case "kill":
                        try:
                            del udp_data[target]
                            del tcp_data[target]

                            for client_ in clients.copy():
                                if client_ != client:
                                    print(f"sending sig to kill {target}")
                                    client_.send(f"kill|{target}".encode())

                                if client_.getpeername() == client_addr:
                                    clients.remove(client_)

                        except BaseException as e:
                            alert("Failed to kill player", e)

                    case "damage":
                        try:
                            tcp_data[target]["health"] = max(
                                tcp_data[target]["health"] - int(args[0]), 0
                            )

                            for client_ in clients.copy():
                                if target == str(client_.getpeername()):
                                    client_.send(f"take_damage|{args[0]}".encode())
                        except BaseException as e:
                            alert("Failed to damage player", e)

            except BaseException as e:
                alert("Error sending TCP message", e)

    except BaseException as e:
        print(f"Could not handle client {client_addr}", e)

    client.close()
    print(f"Closed connection with {client_addr}")


# UDP
Thread(target=receive_udp).start()

while True:
    # TCP
    try:
        client, client_addr = server_tcp.accept()
        clients.append(client)
        print(f"New connection from {client_addr}")
        Thread(target=receive_tcp, args=(client, client_addr)).start()

    except ConnectionAbortedError:
        print(f"{Colors.RED}Connection aborted!{Colors.RESET}")
        break

    except BaseException:
        break

server_tcp.close()
server_udp.close()
