import socket
from threading import Thread

ip, port = "127.0.0.1", 6969

server_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_udp.bind((ip, port))

server_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_tcp.bind((ip, port))
server_tcp.listen(10)


def receive_udp():
    message = None

    while not message:
        data, addr = server_udp.recvfrom(2 ** 12)
        if data:
            message = data.decode()

    return message


def receive_tcp(client):
    while True:
        try:
            data = client.recv(2 ** 12).decode()
            print(data)
        except:
            break
    client.close()


#UDP
Thread(target=receive_udp, daemon=True).start()

#TCP
while True:
    try:
        conn, addr = server_tcp.accept()
        ip = addr[0]
        print(f"Connected to {ip}")
        Thread(target=receive_tcp, args=(conn,)).start()
    except ConnectionAbortedError:
        break
