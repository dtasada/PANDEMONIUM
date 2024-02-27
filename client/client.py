import pygame
from pygame._sdl2.video import Window, Renderer, Texture, Image
import sys
from math import sin, cos, tan, atan2, pi, radians, degrees, sqrt
import csv
from pathlib import Path

import socket
from threading import Thread
from .constants import *


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
            self.sendto(message.encode(), self.target_server)
        if self.conn_type == "tcp":
            self.send(message.encode())


def receive_udp():
    message = None
    while not message:
        data, addr = client_udp.recvfrom(2 ** 12)
        if data:
            message = data.decode()
    return message


def receive_tcp():
    pass


def send():
    client_tcp.send_str("")  # boilerplate


def fill_rect(renderer, color, rect):
    renderer.draw_color = color
    renderer.fill_rect(rect)


def draw_rect(renderer, color, rect):
    renderer.draw_color = color
    renderer.draw_rect(rect)


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
        self.rects = []
        self.tile_size = 40
        for y, row in enumerate(self.map):
            for x, block in enumerate(row):
                if block != 0:
                    rect = pygame.Rect((x * self.tile_size, y * self.tile_size, self.tile_size, self.tile_size))
                    self.rects.append(rect)
        self.map_height = len(self.map)
        self.map_width = len(self.map[0])

    def render_map(self):
        for y, row in enumerate(self.map):
            for x, tile in enumerate(row):
                if tile == 1:
                    fill_rect(
                        display.renderer,
                        RED,
                        (x * self.tile_size, y * self.tile_size, self.tile_size, self.tile_size),
                    )

        for y in range(self.map_height):
            draw_line(display.renderer, WHITE, (0, y * self.tile_size), (self.map_width * self.tile_size, y * self.tile_size))
        for x in range(self.map_width):
            draw_line(display.renderer, WHITE, (x * self.tile_size, 0), (x * self.tile_size, self.map_height * self.tile_size))


class Player:
    def __init__(self):
        self.x = game.tile_size * 6
        self.y = game.tile_size * 3
        self.w = 10
        self.h = 10
        self.color = WHITE
        self.angle = 0.38
        self.rect = pygame.FRect((self.x, self.y, self.w, self.h))

    def draw(self):
        draw_rect(display.renderer, self.color, (self.rect.x - self.w / 2, self.rect.y - self.h / 2, self.w, self.h))

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
        vxvel, vyvel = angle_to_vel(self.angle, vmult * 4)
        p1 = (self.rect.x, self.rect.y)
        p2 = (p1[0] + vxvel * 100, p1[1] + vyvel * 100)

        # draw_line(display.renderer, YELLOW, p1, p2)

        for o in range(-(game.fov // 2), game.fov // 2 + 1):
            self.cast_ray(o)

        # x-col
        self.rect.x += xvel
        for rect in game.rects:
            if self.rect.colliderect(rect):
                if xvel >= 0:
                    self.rect.right = rect.left
                else:
                    self.rect.left = rect.right
        self.rect.y += yvel
        for rect in game.rects:
            if self.rect.colliderect(rect):
                if yvel >= 0:
                    self.rect.bottom = rect.top
                else:
                    self.rect.top = rect.bottom

    def cast_ray(self, offset):
        offset = radians(offset)
        offset = 0
        angle = self.angle + offset
        dx = cos(angle)
        dy = sin(angle)
        #
        tot_length = 0
        y_length = x_length = 0
        #
        cur_tile = [int(self.rect.x / game.tile_size), int(self.rect.y / game.tile_size)]
        cur_pos = list(self.rect.topleft)
        cur_tile_pos = (cur_tile[0] * game.tile_size, cur_tile[1] * game.tile_size)
        # first_dx = cur_tile_pos[0] - 

        x_length_pos = list(self.rect.topleft)
        y_length_pos = list(self.rect.topleft)
        y_length += sqrt(1 + (dx / dy) ** 2)
        x_length += sqrt(1 + (dy / dx) ** 2)
        for _ in range(30):
            if x_length <= y_length:
                cur_tile[0] += 1
                x_length_pos[0] += game.tile_size
                x_length_pos[1] += game.tile_size * (dy / dx)
                x_length += sqrt(1 + (dy / dx) ** 2)
                if game.map[cur_tile[1]][cur_tile[0]] != 0:
                    final_pos = x_length_pos
                    break
            else:
                cur_tile[1] += 1
                y_length_pos[1] += game.tile_size
                y_length_pos[0] += game.tile_size * (dx / dy)
                y_length += sqrt(1 + (dx / dy) ** 2)
                if game.map[cur_tile[1]][cur_tile[0]] != 0:
                    final_pos = y_length_pos
                    break
        p1 = self.rect.topleft
        p2 = final_pos
        draw_line(display.renderer, GREEN, p1, p2)

    def update(self):
        self.keys()
        self.draw()


pygame.init()
display = Display(1280, 720, "PANDEMONIUM")
game = Game()
player = Player()
clock = pygame.time.Clock()
client_udp = client_tcp = None


def main(multiplayer):
    global client_udp, client_tcp
    #
    if multiplayer:
        client_udp = Client("udp")
        client_tcp = Client("tcp")
        Thread(target=receive_udp, daemon=True).start()
    #
    while game.running:
        clock.tick(game.fps)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game.running = False
            elif event.type == pygame.MOUSEMOTION:
                pass
                # player.angle += event.rel[0] / game.sens
                # player.angle %= 2 * pi

        display.renderer.clear()
        fill_rect(
            display.renderer, (40, 40, 40, 255), (0, 0, display.width, display.height)
        )

        game.render_map()
        player.update()

        display.renderer.present()

    pygame.quit()
    sys.exit()
