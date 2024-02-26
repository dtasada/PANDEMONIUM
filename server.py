import socket
from threading import Thread


server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind((socket.gethostname(), 6969)) 

while True:
    data, addr = server.recvfrom(4096)
    print(data.decode())
    message = ("Hello Wordle!")
    socket.sendto(message.encode("utf-8"), addr)


