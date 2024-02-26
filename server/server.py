import socket
from threading import Thread


server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind(("127.0.0.1", 6969)) 

def receive():
    message = None

    while not message:
        data, addr = server.recvfrom(4096)
        if data:
            message = data.decode()

    return message

# while True:
Thread(target=receive, daemon=True).start()
