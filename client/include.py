from enum import Enum
from math import sin, cos, tan, atan2, pi, radians, degrees, sqrt
from pathlib import Path
from pygame._sdl2.video import Window, Renderer, Texture, Image
from random import randint as rand
from time import perf_counter
from typing import List
import csv
import pygame
import socket
import sys

SERVER_ADDRESS, SERVER_PORT = (
    socket.gethostbyname(
        socket.gethostname()
    ),  # Only when developing and playing on same machine
    6969,
)

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
    LIGHT_BLUE = (0, 150, 255)

    ANSI_GREEN = "\033[1;32m"
    ANSI_RED = "\033[1;31;31m"
    ANSI_RESET = "\033[0m"


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


class Display:
    def __init__(self, width, height, title, fullscreen=False, vsync=False):
        self.title = width, height, title
        if fullscreen:
            self.width = pygame.display.Info().current_w
            self.height = pygame.display.Info().current_h
        else:
            self.width, self.height = width, height
        self.center = (self.width / 2, self.height / 2)
        self.window = Window(size=(self.width, self.height))
        self.renderer = Renderer(self.window, vsync=vsync)


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
        is_slider=False,
        slider_display=None,
    ):
        self.content = content
        self.color = self.initial_color = color
        self.font_size = font_size
        self.action = action
        self.should_background = should_background
        self.anchor = anchor
        self.is_slider = is_slider
        self.slider_display = slider_display

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

        if is_slider:
            self.left_slider_tex = Texture.from_surface(
                display.renderer,
                pygame.image.load(
                    Path("client", "assets", "images", "slider_arrow.png")
                ),
            )
            self.left_slider_rect = self.left_slider_tex.get_rect()
            setattr(
                self.left_slider_rect,
                "midleft",
                (self.rect.right + 4, self.rect.midright[1]),
            )

            self.right_slider_tex = Texture.from_surface(
                display.renderer,
                pygame.transform.flip(
                    pygame.image.load(
                        Path("client", "assets", "images", "slider_arrow.png")
                    ),
                    True,
                    False,
                ),
            )
            self.right_slider_rect = self.right_slider_tex.get_rect()

            self.slider_display_rect = write(
                self.anchor,
                self.slider_display,
                v_fonts[self.font_size],
                Colors.WHITE,
                self.left_slider_rect.x + 16,
                self.rect.y,
            )[1]

            if self.slider_display_rect:
                setattr(
                    self.right_slider_rect,
                    self.anchor,
                    (
                        self.slider_display_rect.right,
                        self.rect.y + 8,
                    ),
                )

    def process_event(self, event):
        if self.action is not None:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if self.is_slider:
                        if self.left_slider_rect.collidepoint(pygame.mouse.get_pos()):
                            self.action(-10)
                        if self.right_slider_rect.collidepoint(pygame.mouse.get_pos()):
                            self.action(10)
                    else:
                        self.action()

    def update(self):
        if (
            self.rect.collidepoint(pygame.mouse.get_pos())
            and not self.is_slider
            and self.action is not None
        ):
            display.renderer.blit(self.hover_tex, self.hover_rect)
        if self.should_background:
            fill_rect(Colors.GRAY, self.rect)
        if self.is_slider:
            display.renderer.blit(self.left_slider_tex, self.left_slider_rect)
            display.renderer.blit(self.right_slider_tex, self.right_slider_rect)

            self.slider_display_rect = write(
                self.anchor,
                self.slider_display,
                v_fonts[self.font_size],
                Colors.WHITE,
                self.left_slider_rect.x + 16,
                self.rect.y,
            )[1]

        write(
            "topleft",
            self.content,
            v_fonts[self.font_size],
            self.color,
            self.rect.x,
            self.rect.y,
            tex=False,
        )


class HUD:
    def __init__(self):
        self.health_font_size = 64
        self.health_tex_rect = None
        self.ammo_tex_rect = None

    def health(self, health, has_changed):
        if has_changed or self.health_tex_rect is None:
            return write(
                "bottomleft",
                "HP: " + str(health),
                v_fonts[self.health_font_size],
                Colors.WHITE,
                16,
                display.height - 4,
            )

    def ammo(self, ammo_count, has_changed):
        if has_changed or self.ammo_tex_rect is None:
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


display = Display(1280, 720, "PANDEMONIUM", fullscreen=False, vsync=False)


class Client(socket.socket):
    def __init__(self, conn):
        self.conn_type = conn
        super().__init__(
            socket.AF_INET,
            socket.SOCK_DGRAM if self.conn_type == "udp" else socket.SOCK_STREAM,
        )
        self.target_server = (SERVER_ADDRESS, SERVER_PORT)
        self.current_message = None
        if self.conn_type == "tcp":
            try:
                self.connect(self.target_server)
                print(f"{Colors.ANSI_GREEN}Connected to the server!{Colors.ANSI_RESET}")
            except ConnectionRefusedError as err:
                sys.exit(
                    f"{Colors.ANSI_RED}Could not connect to the server: {Colors.ANSI_RESET}{err}"
                )

    def req(self, message):
        if self.conn_type == "udp":
            self.sendto(str(message).encode(), self.target_server)

        if self.conn_type == "tcp":
            self.send(str(message).encode())

    def req_res(self, *messages):
        for message in messages:
            if self.conn_type == "udp":
                self.sendto(str(message).encode(), self.target_server)

            if self.conn_type == "tcp":
                self.send(str(message).encode())

            response = None
            while not response:
                data, addr = self.recvfrom(2**12)
                if data:
                    response = data.decode()

            return response

    def receive(self):
        if self.conn_type == "udp":
            while True:
                data, addr = self.recvfrom(2**12)
                self.current_message = data.decode()

        elif self.conn_type == "tcp":
            pass


def timgload3(*path, return_rect=False):
    tex = Texture.from_surface(
        display.renderer, pygame.transform.scale_by(pygame.image.load(Path(*path)), 3)
    )

    if return_rect:
        rect = tex.get_rect(topleft=return_rect)
        return tex, rect
    return tex


def timgload(*path, return_rect=False):
    tex = Texture.from_surface(
        display.renderer, pygame.image.load(Path(*path))
    )
    if return_rect:
        rect = tex.get_rect(topleft=return_rect)
        return tex, rect
    return tex


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


def load_map_from_csv(path_, int_=True):
    with open(path_, "r") as f:
        reader = csv.reader(f)
        return [[int(x) if int_ else x.lstrip() for x in line] for line in reader]


def write(
    anchor: str,
    content: str | int,
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


def borderize(img, color, thickness=1):
    mask = pygame.mask.from_surface(img)
    mask_surf = mask.to_surface(setcolor=color)
    mask_surf.set_colorkey(Colors.BLACK)
    surf = pygame.Surface([s + thickness * 2 for s in mask_surf.get_size()], pygame.SRCALPHA)
    poss = [[c * thickness for c in p] for p in [[1, 0], [2, 1], [1, 2], [0, 1]]]
    for pos in poss:
        surf.blit(mask_surf, pos)
    surf.blit(img, (thickness, thickness))
    return surf


cursor = Cursor()

client_udp = None
client_tcp = None

weapon_costs = {
    "1": 1200,
}
