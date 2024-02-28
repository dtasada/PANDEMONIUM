import pygame
from pygame._sdl2.video import Window, Renderer, Texture, Image
import sys
from math import sin, cos, tan, atan2, pi, radians, degrees, sqrt
import csv
from pathlib import Path

import socket
from threading import Thread
from .constants import *


def disable_mouse():
    pygame.mouse.set_visible(False)
    display.window.grab_mouse = True


def write(surf, anchor, text, font, color, x, y, alpha=255, blit=True, border=None, special_flags=0, tex=True):
    if border is not None:
        bc, bw = border, 1
        write(surf, anchor, text, font, bc, x - bw, y - bw),
        write(surf, anchor, text, font, bc, x + bw, y - bw),
        write(surf, anchor, text, font, bc, x - bw, y + bw),
        write(surf, anchor, text, font, bc, x + bw, y + bw)
    text = font.render(str(text), True, color)
    if tex:
        text = Texture.from_surface(surf, text)
        text.alpha = alpha
    else:
        text.set_alpha(alpha)
    text_rect = text.get_rect()
    setattr(text_rect, anchor, (int(x), int(y)))
    if blit:
        surf.blit(text, text_rect, special_flags=special_flags)
    return text, text_rect


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
        data, addr = client_udp.recvfrom(2**12)
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


class Button:
    def __init__(self):
        pass
        # todo fucking button


class Display:
    def __init__(self, width, height, title, fullscreen=False):
        self.title = width, height, title
        if fullscreen:
            self.width = pygame.display.Info().current_w
            self.height = pygame.display.Info().current_h
        else:
            self.width, self.height = width, height
        self.center = (self.width / 2, self.height / 2)
        self.window = Window(size=(self.width, self.height))
        self.renderer = Renderer(self.window)


class Game:
    def __init__(self):
        self.running = True
        self.stage = "play"
        self.fps = 60
        self.sens = 0.0005
        self.fov = 60
        self.map = load_map_from_csv(Path("client", "assets", "map.csv"))
        self.rects = []
        self.tile_size = 40
        for y, row in enumerate(self.map):
            for x, block in enumerate(row):
                if block != 0:
                    rect = pygame.Rect(
                        (
                            x * self.tile_size,
                            y * self.tile_size,
                            self.tile_size,
                            self.tile_size,
                        )
                    )
                    self.rects.append(rect)
        self.map_height = len(self.map)
        self.map_width = len(self.map[0])

    def render_map(self):
        for y, row in enumerate(self.map):
            for x, tile in enumerate(row):
                if tile == 0:
                    color = DARK_GRAY
                elif tile == 1:
                    color = RED
                fill_rect(
                    display.renderer,
                    color,
                    (
                        x * self.tile_size,
                        y * self.tile_size,
                        self.tile_size,
                        self.tile_size,
                    ),
                )

        for y in range(self.map_height):
            draw_line(
                display.renderer,
                WHITE,
                (0, y * self.tile_size),
                (self.map_width * self.tile_size, y * self.tile_size),
            )
        for x in range(self.map_width):
            draw_line(
                display.renderer,
                WHITE,
                (x * self.tile_size, 0),
                (x * self.tile_size, self.map_height * self.tile_size),
            )


class Player:
    def __init__(self):
        self.x = game.tile_size * 6
        self.y = game.tile_size * 3
        self.w = 10
        self.h = 10
        self.color = WHITE
        self.angle = 0.38
        self.rect = pygame.FRect((self.x, self.y, self.w, self.h))
        self.should_render = False

    def draw(self):
        draw_rect(
            display.renderer, self.color, (self.rect.x, self.rect.y, self.w, self.h)
        )

    def keys(self):
        if game.stage == "play":
            vmult = 2
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
            amult = 0.03
            if keys[pygame.K_LEFT]:
                self.angle -= amult
            if keys[pygame.K_RIGHT]:
                self.angle += amult

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

        for o in range(-(game.fov // 2), game.fov // 2 + 1):
            self.cast_ray(o)
        _xvel, _yvel = angle_to_vel(self.angle)
        m = 20
        p1 = self.rect.center
        p2 = (self.rect.centerx + _xvel * m, self.rect.centery + _yvel * m)
        if self.should_render:
            draw_line(display.renderer, BLACK, p1, p2)

    def cast_ray(self, deg_offset):
        offset = radians(deg_offset)
        angle = self.angle + offset
        dx = cos(angle)
        dy = sin(angle)
        #
        tot_length = 0
        y_length = x_length = 0
        start_x, start_y = [
            self.rect.centerx / game.tile_size,
            self.rect.centery / game.tile_size,
        ]
        cur_x, cur_y = [int(start_x), int(start_y)]
        hypot_x, hypot_y = sqrt(1 + (dy / dx) ** 2), sqrt(1 + (dx / dy) ** 2)
        direc = (dx, dy)
        #
        if dx < 0:
            step_x = -1
            x_length = (start_x - cur_x) * hypot_x
        else:
            step_x = 1
            x_length = (cur_x + 1 - start_x) * hypot_x
        if dy < 0:
            step_y = -1
            y_length = (start_y - cur_y) * hypot_y
        else:
            step_y = 1
            y_length = (cur_y + 1 - start_y) * hypot_y

        col = False
        dist = 0
        max_dist = 300
        while not col and dist < max_dist:
            if x_length < y_length:
                cur_x += step_x
                dist = x_length
                x_length += hypot_x
            else:
                cur_y += step_y
                dist = y_length
                y_length += hypot_y
            if game.map[cur_y][cur_x] != 0:
                col = True
        if col:
            # calculations
            p1 = (start_x * game.tile_size, start_y * game.tile_size)
            p2 = (
                p1[0] + dist * dx * game.tile_size,
                p1[1] + dist * dy * game.tile_size,
            )
            ray_mult = 1
            # 3D
            dist *= ray_mult
            dist_px = dist * game.tile_size
            wh = min(display.height * game.tile_size / dist_px, display.height)
            ww = display.width / game.fov
            wx = (deg_offset + game.fov / 2) / game.fov * display.width
            wy = display.height / 2 - wh / 2
            m = 0.1
            fill_rect(
                display.renderer,
                [wh / display.height * 255] * 3 + [255],
                (wx, wy, ww, wh),
            )
            if self.should_render:
                # raying the 2D rays
                draw_line(display.renderer, GREEN, p1, p2)

    def update(self):
        self.keys()
        if self.should_render:
            self.draw()


display = Display(1280, 720, "PANDEMONIUM", True)
game = Game()
player = Player()
clock = pygame.time.Clock()
client_udp = client_tcp = None
black_square = pygame.Surface((display.width, display.height), pygame.SRCALPHA)
black_square.fill(BLACK)
black_square.set_alpha(40)
black_square = Texture.from_surface(display.renderer, black_square)
black_square_rect = black_square.get_rect()
disable_mouse()


def main(multiplayer):
    global client_udp, client_tcp
    #
    if multiplayer:
        client_udp = Client("udp")
        client_tcp = Client("tcp")
        Thread(target=receive_udp, daemon=True).start()
        Thread(target=receive_tcp, daemon=True).start()
    #
    while game.running:
        clock.tick(game.fps)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game.running = False
            elif event.type == pygame.MOUSEMOTION:
                # pass
                if game.stage == "play":
                    player.angle += event.rel[0] * game.sens
                    player.angle %= 2 * pi

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game.stage = {"play": "settings", "settings": "play"}[game.stage]

        display.renderer.clear()
        fill_rect(
            display.renderer, DARK_GRAY, (0, 0, display.width, display.height / 2)
        )
        fill_rect(
            display.renderer,
            BROWN,
            (0, display.height / 2, display.width, display.height / 2),
        )

        if player.should_render:
            game.render_map()
        player.update()
        if game.stage == "settings":
            display.renderer.blit(black_square, black_square_rect)
            write(display.renderer, "center", "PANDEMONIUM", v_fonts[100], WHITE, display.width / 2, 150)

        display.renderer.present()

    pygame.quit()
    sys.exit()
