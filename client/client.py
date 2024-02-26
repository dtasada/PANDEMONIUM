import pygame
from pygame._sdl2.video import Window, Renderer, Texture, Image
import sys
from math import sin, cos, tan, atan2, pi
import csv
from pathlib import Path

import socket
from threading import Thread


class Client(socket.socket):
    def __init__(self, conn):
        self.conn_type = conn
        super().__init__(
            socket.AF_INET,
            socket.SOCK_DGRAM if self.conn_type == "udp" else socket.SOCK_STREAM,
        )
        self.target_server = ("127.0.0.1", 6969)
        if self.conn_type == "tcp":
            self.connect(self.target_server)

    def send_str(self, message):
        if self.conn_type == "udp":
            self.sendto(message.encode("utf-8"), self.target_server)
        if self.conn_type == "tcp":
            self.send(message.encode("utf-8"))


clientUDP = Client("udp")
clientTCP = Client("tcp")


def receiveUDP():
    message = None

    while not message:
        data, addr = clientUDP.recvfrom(4096)
        if data:
            message = data.decode()

    return message


def receiveTCP():
    pass


def send():
    clientTCP.send_str("")  # boilerplate


def fill_rect(renderer, color, rect):
    renderer.draw_color = color
    renderer.fill_rect(rect)


def draw_line(renderer, color, p1, p2):
    renderer.draw_color = color
    renderer.draw_line(p1, p2)


def angle_to_vel(angle, speed=1):
    return cos(angle) * speed, sin(angle) * speed


def load_map_from_csv(path_):
    with open(path_, "r") as f:
        reader = csv.reader(f)
        return [[int(x) for x in line] for line in reader]


class Display:
    def __init__(self, width, height, title):
        self.width, self.height, self.title = width, height, title
        self.center = (self.width / 2, self.height / 2)
        self.window = Window(size=(self.width, self.height))
        self.renderer = Renderer(self.window)


class Game:
    def __init__(self):
        self.running = True
        self.fps = 60
        self.sens = 200
        self.fov = 60
        self.map = load_map_from_csv(Path("client", "assets", "map.csv"))

    def render_map(self):
        size = 20
        for y, row in enumerate(self.map):
            for x, tile in enumerate(row):
                if tile == 1:
                    fill_rect(
                        display.renderer,
                        (255, 0, 0, 255),
                        (x * size, y * size, size, size),
                    )

        for y, row in enumerate(self.map):
            draw_line(
                display.renderer,
                (255, 255, 255, 255),
                (0, (y + 1) * size),
                (10 * size, (y + 1) * size),
            )
            for x, tile in enumerate(row):
                if y == 0:
                    draw_line(
                        display.renderer,
                        (255, 255, 255, 255),
                        ((x + 1) * size, 0),
                        ((x + 1) * size, 10 * size),
                    )


class Player:
    def __init__(self):
        self.x = 10
        self.y = 10
        self.w = 10
        self.h = 10
        self.color = (160, 160, 160, 255)
        self.angle = 0

    def draw(self):
        fill_rect(display.renderer, self.color, (self.x, self.y, self.w, self.h))

    def keys(self):
        vmult = 1
        keys = pygame.key.get_pressed()
        xvel = yvel = 0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            xvel, yvel = angle_to_vel(self.angle, vmult)
        if keys[pygame.K_a]:
            xvel, yvel = angle_to_vel(self.angle - pi / 2, vmult)
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            xvel, yvel = angle_to_vel(self.angle + pi, vmult)
        if keys[pygame.K_d]:
            xvel, yvel = angle_to_vel(self.angle + pi / 2, vmult)
        if keys[pygame.K_LEFT]:
            self.angle -= 0.05
        if keys[pygame.K_RIGHT]:
            self.angle += 0.05
        vxvel, vyvel = angle_to_vel(self.angle, vmult)
        p1 = (self.x + self.w / 2, self.y + self.h / 2)
        p2 = (p1[0] + vxvel * 100, p1[1] + vyvel * 100)

        draw_line(display.renderer, (255, 255, 0, 255), p1, p2)

        for o in range(-(game.fov // 2), game.fov // 2 + 1):
            self.cast_ray(o)

        self.x += xvel
        self.y += yvel

    def cast_ray(self, angle):
        print(angle)

    def update(self):
        self.keys()
        self.draw()


pygame.init()
display = Display(1280, 720, "PANDEMONIUM")
player = Player()
game = Game()
clock = pygame.time.Clock()


def main():
    Thread(target=receiveUDP, daemon=True).start()
    while game.running:
        clock.tick(game.fps)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game.running = False
            elif event.type == pygame.MOUSEMOTION:
                player.angle += event.rel[0] / game.sens
                player.angle %= 2 * pi

        display.renderer.clear()
        fill_rect(
            display.renderer, (40, 40, 40, 255), (0, 0, display.width, display.height)
        )

        game.render_map()
        player.update()

        display.renderer.present()

    pygame.quit()
    sys.exit()
