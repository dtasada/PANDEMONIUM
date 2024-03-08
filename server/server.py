#!/usr/bin/env python3
import sys
import socket
import json
from threading import Thread


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

def receive_udp():
    while True:
        data, addr = server_udp.recvfrom(2**12)
        if data.decode() != "quit":
            addresses[str(addr)] = json.loads(data)

            for address in addresses:
                response = json.dumps({k: v for k, v in addresses.items() if k != address})
                server_udp.sendto(response.encode(), eval(address))
        else:
            print(addresses)
            del addresses[str(addr)]
            print(addresses)


def receive_tcp(client, client_addr):
    try:
        while True:
            data = client.recv(2**12).decode()
            if not data:
                break

            # concoct response
            response = "example response"
            client.send(response.encode("utf-8"))
    except Exception as err:
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
        print(f"New connection from {client_addr}")
        Thread(target=receive_tcp, args=(client, client_addr)).start()

    except ConnectionAbortedError:
        print(f"{Colors.ANSI_RED}Connection aborted!{Colors.ANSI_RESET}")
        break
    except KeyboardInterrupt:
        break

server_tcp.close()
