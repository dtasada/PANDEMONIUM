from enum import Enum
from math import sin, cos, tan, atan2, pi, radians, degrees, sqrt
from pathlib import Path
from pygame._sdl2.video import Window, Renderer, Texture, Image

import csv
import pygame
import socket
import sys


pygame.init()


class Colors:
    BLACK = (0, 0, 0, 255)
    BLUE = (0, 0, 255, 255)
    DARK_GRAY = (40, 40, 40, 255)
    GRAY = (150, 150, 150, 255)
    LIGHT_GRAY = (220, 220, 220, 255)
    GREEN = (0, 255, 0, 255)
    BROWN = (97, 54, 19)
    ORANGE = (255, 140, 0, 255)
    RED = (255, 0, 0, 255)
    WHITE = (255, 255, 255, 255)
    YELLOW = (255, 255, 0, 255)


class States(Enum):
    MAIN_MENU = 0
    SETTINGS = 1
    PLAY = 2


class Signal(Enum):
    DECREASE_HEALTH = 0


v_fonts = [
    pygame.font.Font(Path("client", "assets", "fonts", "VT323-Regular.ttf"), i)
    for i in range(101)
]


current_message = None


def receive_udp():
    global current_message

    while not current_message:
        data, addr = client_udp.recvfrom(2**12)
        if data:
            current_message = data.decode()


def receive_tcp():
    pass


def fill_rect(color, rect):
    display.renderer.draw_color = color
    display.renderer.fill_rect(rect)


def draw_rect(color, rect):
    display.renderer.draw_color = color
    display.renderer.draw_rect(rect)


def draw_line(color, p1, p2):
    display.renderer.draw_color = color
    display.renderer.draw_line(p1, p2)


def angle_to_vel(angle, speed=1):
    return cos(angle) * speed, sin(angle) * speed


def load_map_from_csv(path_):
    with open(path_, "r") as f:
        reader = csv.reader(f)
        return [[int(x) for x in line] for line in reader]


def write(
    anchor: str,
    content: str,
    font: pygame.Font,
    color: tuple,
    x: int,
    y: int,
    alpha=255,
    blit=True,
    border=None,
    special_flags=0,
    tex=True,
):
    if border is not None:
        bc, bw = border, 1
        write(anchor, content, font, bc, x - bw, y - bw)
        write(anchor, content, font, bc, x + bw, y - bw)
        write(anchor, content, font, bc, x - bw, y + bw)
        write(anchor, content, font, bc, x + bw, y + bw)
    tex = font.render(str(content), True, color)
    if tex:
        tex = Texture.from_surface(display.renderer, tex)
        tex.alpha = alpha
    else:
        tex.set_alpha(alpha)
    rect = tex.get_rect()

    setattr(rect, anchor, (int(x), int(y)))

    if blit:
        display.renderer.blit(tex, rect, special_flags=special_flags)

    return tex, rect


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


class Cursor:
    def __init__(self):
        self.surf = pygame.image.load(Path("client", "assets", "images", "cursor.png"))
        self.tex = Texture.from_surface(display.renderer, self.surf)
        self.rect = self.surf.get_rect()
        self.topleft = pygame.Rect(self.rect.topleft, (1, 1))
        self.enabled = True
        pygame.mouse.set_visible(False)

    def enable(self):
        self.enabled = True
        self.should_wrap = False
        display.window.grab_mouse = False

    def disable(self):
        self.enabled = False
        display.window.grab_mouse = True
        self.should_wrap = True

    def update(self):
        self.rect.topleft = self.topleft.topleft = pygame.mouse.get_pos()
        display.renderer.blit(self.tex, self.rect)


class Button:
    def __init__(
        self,
        x,
        y,
        content,
        action,
        width=None,
        height=None,
        font_size=32,
        color=Colors.LIGHT_GRAY,
        should_background=False,
        anchor="topleft",
    ):
        self.content = content
        self.color = self.initial_color = color
        self.font_size = font_size
        self.action = action
        self.should_background = should_background
        self.anchor = anchor

        self.font = v_fonts[self.font_size]
        self.width = width or self.font.size(content)[0]
        self.height = height or self.font.size(content)[1]
        self.rect = pygame.Rect(0, 0, self.width, self.height)
        setattr(self.rect, self.anchor, (x, y))

        if action is not None:
            self.hover_tex = Texture.from_surface(
                display.renderer,
                pygame.image.load(Path("client", "assets", "images", "hover.png")),
            )
            self.hover_rect = self.hover_tex.get_rect(
                midright=(self.rect.x - 16, self.rect.centery)
            )

    def process_event(self, event):
        if self.action is not None:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if self.rect.collidepoint(pygame.mouse.get_pos()):
                        self.action()

    def update(self):
        if self.action is not None:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                display.renderer.blit(self.hover_tex, self.hover_rect)
        if self.should_background:
            fill_rect(Colors.GRAY, self.rect)
        write(
            "topleft",
            self.content,
            v_fonts[self.font_size],
            self.color,
            self.rect.x,
            self.rect.y,
            tex=False,
        )


display = Display(1280, 720, "PANDEMONIUM", fullscreen=False)


class HUD:
    def __init__(self):
        self.health_font_size = 64

    def health(self, health, has_changed):
        return write(
            "bottomleft",
            "HP: " + str(health),
            v_fonts[self.health_font_size],
            Colors.WHITE,
            16,
            display.height - 4,
        )

    def ammo(self, ammo_count, has_changed):
        return write(
            "bottomright",
            ammo_count,
            v_fonts[self.health_font_size],
            Colors.WHITE,
            display.width - 16,
            display.height - 4,
        )

    def ammo_update(self, ammo_count, has_changed):
        display.renderer.blit(*self.ammo(ammo_count, has_changed))

    def health_update(self, health, has_changed):
        display.renderer.blit(*self.health(health, has_changed))


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

    def req_res(self, *messages):
        for message in messages:
            if self.conn_type == "udp":
                self.sendto(message.encode(), self.target_server)
            if self.conn_type == "tcp":
                self.send(message.encode())

            message = None
            while not message:
                data, addr = client_udp.recvfrom(2**12)
                if data:
                    message = data.decode()

            return message


client_udp: Client = None
client_tcp: Client = None

cursor = Cursor()
