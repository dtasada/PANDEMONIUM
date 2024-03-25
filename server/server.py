#!/usr/bin/env python3
import sys
import socket
import json
from threading import Thread
from pprint import pprint


class Colors:
    ANSI_GREEN = "\033[1;32m"
    ANSI_RED = "\033[1;31;31m"
    ANSI_RESET = "\033[0m"


SERVER_ADDRESS, SERVER_PORT = socket.gethostbyname(socket.gethostname()), 6969

try:
    server_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_udp.bind((SERVER_ADDRESS, SERVER_PORT))
    print(
        f"{Colors.ANSI_GREEN}UDP server is listening at {SERVER_ADDRESS}:{SERVER_PORT}{Colors.ANSI_RESET}"
    )
except Exception as err:
    sys.exit(
        f"{Colors.ANSI_RED}UDP server failed to initialize: {Colors.ANSI_RESET}{err}"
    )


try:
    server_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_tcp.bind((SERVER_ADDRESS, SERVER_PORT))
    server_tcp.listen(10)
    print(
        f"{Colors.ANSI_GREEN}TCP server is listening at {SERVER_ADDRESS}:{SERVER_PORT}{Colors.ANSI_RESET}"
    )
except Exception as err:
    sys.exit(
        f"{Colors.ANSI_RED}TCP server failed to initialize: {Colors.ANSI_RESET}{err}"
    )


addresses = {}
clients = []


def receive_udp():
    while True:
        request, addr = server_udp.recvfrom(2**12)
        request = json.loads(request)
        addresses[request["tcp_id"]] = request["body"]

        addresses[request["tcp_id"]]["udp_id"] = addr

        for tcp_id, content in addresses.items():
            response = {k: v for k, v in addresses.items() if k != tcp_id}
            response = json.dumps(response)
            server_udp.sendto(response.encode(), content["udp_id"])


def receive_tcp(client, client_addr):
    try:
        while True:
            data = client.recv(2**12).decode()
            verb = data.split("-")[0]
            target = data.split("-")[1]

            try:
                match verb:
                    case "quit":
                        for client_ in clients:
                            if client_ != client:
                                client_.send(f"quit-{target}".encode())

                            if client_.getpeername() == client_addr:
                                clients.remove(client_)

                        del addresses[target]

                    case "kill":
                        for client_ in clients:
                            if client_ != client:
                                client_.send(f"kill-{target}".encode())

                            if client_.getpeername() == client_addr:
                                clients.remove(client_)

                        del addresses[client_addr]

            except BaseException as err:
                print(
                    f"{Colors.ANSI_RED}Error sending TCP message:{Colors.ANSI_RESET} {err}"
                )

    except BaseException as err:
        print(
            f"{Colors.ANSI_RED}Could not handle client {client_addr}:{Colors.ANSI_RESET} {err}"
        )

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
        print(f"{Colors.ANSI_RED}Connection aborted!{Colors.ANSI_RESET}")
        break

    except BaseException:
        break

server_tcp.close()
server_udp.close()
