#!/usr/bin/env python3
import sys
import socket
from threading import Thread


class Colors:
    ANSI_GREEN = "\033[1;32m"
    ANSI_RED = "\033[1;31;31m"
    ANSI_RESET = "\033[0m"


SERVER_ADDRESS, SERVER_PORT = "192.168.2.4", 6969

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

addresses = []


def receive_udp():
    while True:
        data, addr = server_udp.recvfrom(2**12)

        if addr not in addresses:
            addresses.append(addr)

        message = data.decode()
        for address in addresses:
            if address == addr:
                continue
            server_udp.sendto(message.encode(), address)


def receive_tcp(client):
    while True:
        data = client.recv(2**12).decode()
        if not data:
            break

        # concoct response
        response = "example response"
        client.send(response.encode("utf-8"))

    client.close()


# UDP
Thread(target=receive_udp).start()

while True:
    # TCP
    try:
        client, addr = server_tcp.accept()  # This is blocking
        print(f"New connection from {addr[0]}")
        Thread(target=receive_tcp, args=(client,)).start()
    except ConnectionAbortedError:
        print(f"{Colors.ANSI_RED}Connection aborted!{Colors.ANSI_RESET}")
    except KeyboardInterrupt:
        break
    finally:
        break

server_tcp.close()
