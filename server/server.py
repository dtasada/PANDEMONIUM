import socket
from threading import Thread

ip, port = "127.0.0.1", 6969

serverUDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
serverUDP.bind((ip, port)) 

serverTCP = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serverTCP.bind((ip, port))
serverTCP.listen(10)

def receiveUDP():
    message = None

    while not message:
        data, addr = serverUDP.recvfrom(4096)
        if data:
            message = data.decode()

    return message

def receiveTCP(client):
    while True:
        try:
            data = client.recv(2 ** 11).decode()
            print(data)
        except:
            break

#UDP
Thread(target=receiveUDP, daemon=True).start()

#TCP
while True:
    try:
        conn, addr = serverTCP.accept()
        ip = addr[0]
        print(f"Connected to {ip}")
        Thread(target=receiveTCP, args=(conn,)).start()
    except ConnectionAbortedError:
        break



