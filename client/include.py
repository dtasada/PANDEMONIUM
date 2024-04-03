from enum import Enum
from math import sin, cos, atan2
from pathlib import Path
from typing import Any, Optional, TypeAlias
from pygame._sdl2.video import Window, Renderer, Texture
import csv
import pygame
import socket
import sys
import json
import os


SERVER_ADDRESS, SERVER_TCP_PORT, SERVER_UDP_PORT = (
    socket.gethostbyname(
        socket.gethostname()
    ),  # Only when developing and playing on same machine
    6969,
    4200,
)

pygame.init()


Color: TypeAlias = tuple[int, int, int, int] | tuple[int, int, int]


class Colors:
    BLACK = (0, 0, 0, 255)
    BLUE = (0, 0, 255, 255)
    BROWN = (97, 54, 19)
    DARK_GRAY = (40, 40, 40, 255)
    GRAY = (150, 150, 150, 255)
    GREEN = (0, 255, 0, 255)
    LIGHT_BLUE = (0, 150, 255)
    LIGHT_GRAY = (220, 220, 220, 255)
    ORANGE = (255, 140, 0, 255)
    PINK = (152, 0, 136, 255)
    RED = (255, 0, 0, 255)
    WHITE = (255, 255, 255, 255)
    YELLOW = (255, 255, 0, 255)

    ANSI_GREEN = "\033[1;32m"
    ANSI_RED = "\033[1;31;31m"
    ANSI_RESET = "\033[0m"

    ANSI_BOLD = "\u001b[1m"
    ANSI_ITALIC = "\u001b[3m"
    ANSI_UNDERLINE = "\u001b[4m"


class Joymap:
    # axes
    LEFT_JOYSTICK_HOR = 0
    LEFT_JOYSTICK_VER = 1
    RIGHT_JOYSTICK_HOR = 2
    RIGHT_JOYSTICK_VER = 3
    LEFT_TRIGGER = 4
    RIGHT_TRIGGER = 5

    # buttons
    CROSS = 0
    CIRCLE = 1
    SQUARE = 2
    TRIANGLE = 3
    LEFT_JOYSTICK_CLICK = 7


class States(Enum):
    LAUNCH = 0
    MAIN_MENU = 1
    MAIN_SETTINGS = 2
    PLAY = 3
    PLAY_SETTINGS = 4


class Directions(Enum):
    UP = 0
    UP_RIGHT = 1
    RIGHT = 2
    DOWN_RIGHT = 3
    DOWN = 4
    DOWN_LEFT = 5
    LEFT = 6
    UP_LEFT = 7


v_fonts = [
    pygame.font.Font(Path("client", "assets", "fonts", "VT323-Regular.ttf"), i)
    for i in range(101)
]
vi_fonts = [
    pygame.font.Font(
        Path("client", "assets", "fonts", "VT323-Regular.ttf", italic=True), i
    )
    for i in range(101)
]


class UserInput:
    def __init__(self, x, y, font_size, color, anchor="center"):
        self.x = x
        self.y = y
        self.text = ""
        self.font_size = font_size
        self.color = color
        self.anchor = anchor

    def process_event(self, event):
        if event.key == pygame.K_BACKSPACE:
            self.text = self.text[:-1]
        elif event.key == pygame.K_RETURN:
            pass
        elif event.key != pygame.K_BACKSPACE:
            self.text += event.unicode

    def update(self):
        if self.text == "":
            text = "enter name"
            font = vi_fonts[self.font_size - 8]
        else:
            text = self.text
            font = v_fonts[self.font_size]
        write(
            self.anchor,
            text,
            font,
            self.color,
            self.x,
            self.y,
        )
        # draw_rect(
        #     Colors.RED,
        #     write(
        #         self.anchor,
        #         text,
        #         font,
        #         self.color,
        #         self.x,
        #         self.y,
        #     )[1],
        # )


class Display:
    def __init__(self, width, height, title, fullscreen=False, vsync=False):
        if fullscreen:
            self.width = pygame.display.Info().current_w
            self.height = pygame.display.Info().current_h
        else:
            self.width, self.height = width, height

        self.center = (self.width / 2, self.height / 2)
        self.window = Window(size=(self.width, self.height), title=title)

        if fullscreen:
            self.window.set_fullscreen()

        self.renderer = Renderer(self.window, vsync=vsync)


class Cursor:
    def __init__(self):
        self.surf = pygame.image.load(
            Path("client", "assets", "images", "menu", "cursor.png")
        )
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
        x: int,
        y: int,
        content: str,
        action: callable,
        width: Optional[int] = None,
        height: Optional[int] = None,
        action_arg: Any = None,
        font_size: int = 32,
        color: Color = Colors.WHITE,
        should_background: bool = False,
        anchor: str = "topleft",
        is_slider: bool = False,
        slider_display: Optional[str] = None,
        grayed_out_when: Optional[callable] = None,
    ):
        self.content = content
        self.color = self.initial_color = color
        self.font_size = font_size
        self.action = action
        self.action_arg = action_arg
        self.should_background = should_background
        self.anchor = anchor
        self.is_slider = is_slider
        self.slider_display = slider_display

        self.font = v_fonts[self.font_size]
        self.width = width or self.font.size(content)[0]
        self.height = height or self.font.size(content)[1]

        self.rect = pygame.Rect(0, 0, self.width, self.height)
        setattr(self.rect, self.anchor, (x, y))
        self.grayed_out_when = grayed_out_when

        if action is not None:
            self.hover_tex = Texture.from_surface(
                display.renderer,
                pygame.image.load(
                    Path("client", "assets", "images", "menu", "hover.png")
                ),
            )
            self.hover_rect = self.hover_tex.get_rect(
                midright=(self.rect.x - 16, self.rect.centery)
            )

        if is_slider:
            self.left_slider_tex = Texture.from_surface(
                display.renderer,
                pygame.image.load(
                    Path("client", "assets", "images", "menu", "slider_arrow.png")
                ),
            )

            self.left_slider_rect = self.left_slider_tex.get_rect(
                midleft=(self.rect.right + 4, self.rect.centery)
            )

            self.right_slider_tex = Texture.from_surface(
                display.renderer,
                pygame.transform.flip(
                    pygame.image.load(
                        Path("client", "assets", "images", "menu", "slider_arrow.png")
                    ),
                    True,
                    False,
                ),
            )
            self.right_slider_rect = self.right_slider_tex.get_rect()

    @property
    def grayed_out(self):
        return self.grayed_out_when is not None and self.grayed_out_when()

    def process_event(self, event):
        if self.action is not None:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if self.is_slider:
                        if self.left_slider_rect.collidepoint(pygame.mouse.get_pos()):
                            self.action(-self.action_arg)
                        if self.right_slider_rect.collidepoint(pygame.mouse.get_pos()):
                            self.action(self.action_arg)

                    elif self.rect.collidepoint(pygame.mouse.get_pos()):
                        if not self.grayed_out:
                            self.action()

    def update(self):
        if (
            self.rect.collidepoint(pygame.mouse.get_pos())
            and not self.is_slider
            and self.action is not None
            and not self.grayed_out
        ):
            display.renderer.blit(self.hover_tex, self.hover_rect)
        if self.should_background:
            fill_rect(Colors.GRAY, self.rect)
        if self.is_slider:
            display.renderer.blit(self.left_slider_tex, self.left_slider_rect)
            display.renderer.blit(self.right_slider_tex, self.right_slider_rect)
            self.slider_display_rect = write(
                "center",
                self.slider_display(),
                v_fonts[self.font_size],
                Colors.WHITE,
                self.rect.right + 45,
                self.rect.centery,
            )[1]

            setattr(
                self.right_slider_rect,
                "midleft",
                (
                    self.rect.right + 15 + 40 + 15,
                    self.rect.centery,
                ),
            )
            setattr(
                self.left_slider_rect,
                "center",
                (
                    self.rect.right + 15,
                    self.rect.centery,
                ),
            )
        tex, rect = write(
            "topleft",
            self.content,
            v_fonts[self.font_size],
            self.color,
            self.rect.x,
            self.rect.y,
            blit=False,
        )
        if self.grayed_out:
            tex.color = (80, 80, 80, 255)
        display.renderer.blit(tex, rect)


display = Display(
    1280,
    720,
    "PANDEMONIUM",
    fullscreen=False if "--no-fullscreen" else True,
    vsync=False if "--no-vsync" else True,
)

class Client(socket.socket):
    def __init__(self, conn):
        self.conn_type = conn
        if self.conn_type == "tcp":
            super().__init__(
                socket.AF_INET,
                socket.SOCK_STREAM,
            )
            self.target_server = (
                SERVER_ADDRESS,
                SERVER_TCP_PORT,
            )
        elif self.conn_type == "udp":
            super().__init__(
                socket.AF_INET,
                socket.SOCK_DGRAM,
            )
            self.target_server = (
                SERVER_ADDRESS,
                SERVER_UDP_PORT,
            )

        self.current_message: str = ""
        if self.conn_type == "tcp":
            try:
                self.connect(self.target_server)
                print(f"{Colors.ANSI_GREEN}Connected to the server!{Colors.ANSI_RESET}")
            except ConnectionRefusedError as err:
                sys.exit(
                    f"{Colors.ANSI_RED}Could not connect to the server: {Colors.ANSI_RESET}{err}\n"
                    + f"{Colors.ANSI_BOLD}Use the {Colors.ANSI_ITALIC}--no-multiplayer{Colors.ANSI_RESET}{Colors.ANSI_BOLD} flag to run the game offline"
                )

    def req(self, message) -> None:
        """
        send message to server without waiting for response
        """
        if self.conn_type == "udp":
            self.sendto(str(message).encode(), self.target_server)

        if self.conn_type == "tcp":
            self.send(str(message).encode())

    def req_res(self, *messages: str) -> str:
        """
        send message to server and wait for response
        """
        for message in messages:
            if self.conn_type == "udp":
                self.sendto(str(message).encode(), self.target_server)

            if self.conn_type == "tcp":
                self.send(str(message).encode())

            response = ""
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
            while True:
                data = self.recv(2**12)
                self.current_message = data.decode()


def normalize_angle(angle: float) -> float:
    """
    Normalizes given angle to 0 - 360 degrees
    """
    angle = positive_angle(angle)
    while angle > 180:
        angle -= 360
    return angle


def positive_angle(angle: float) -> float:
    """
    Makes angle positive
    """
    while angle < 0:
        angle += 360
    return angle


def is_angle_between(a: float, testAngle: float, b: float) -> bool:
    """
    Checks if testAngle is between a and b
    """
    a -= testAngle
    b -= testAngle
    a = normalize_angle(a)
    b = normalize_angle(b)
    if a * b >= 0:
        return False
    return abs(a - b) < 180


def imgload(
    *path_,
    colorkey: tuple[int, int, int] = None,
    frames: int = None,
    whitespace: int = 0,
    frame_pause: int = 0,
    end_frame: int = None,
    scale: int = 1,
    to_tex: bool = True,
    return_rect: bool = False,
) -> tuple[Texture, pygame.Rect]:
    # init
    ret = []
    img = pygame.image.load(Path(*path_))
    # frame loading
    if frames is None:
        frames_used = (1, img.get_width())
    else:
        frames_used = (frames, img.get_width() / frames)
    for i in range(frames_used[0]):
        ret.append(
            img.subsurface(
                i * frames_used[1], 0, frames_used[1] - whitespace, img.get_height()
            )
        )
    for i in range(frame_pause):
        ret.append(ret[0])
    if end_frame is not None:
        ret.append(ret[end_frame])
    # colorkey
    if colorkey is not None:
        for x in ret:
            x.set_colorkey(colorkey)
    if to_tex:
        ret = [
            Texture.from_surface(display.renderer, pygame.transform.scale_by(x, scale))
            for x in ret
        ]
    # final return
    if frames is None:
        ret = ret[0]
        if return_rect:
            ret = (ret, ret.get_rect())
    return ret


def fill_rect(color: Color, rect: pygame.Rect) -> None:
    display.renderer.draw_color = color
    display.renderer.fill_rect(rect)


def draw_rect(color: Color, rect: pygame.Rect) -> None:
    display.renderer.draw_color = color
    display.renderer.draw_rect(rect)


def draw_line(color: Color, p1: tuple[int, int], p2: tuple[int, int]) -> None:
    display.renderer.draw_color = color
    display.renderer.draw_line(p1, p2)


def angle_to_vel(angle: float, speed: float = 1) -> tuple[float, float]:
    """Convert een richting naar twee snelheidsvectoren"""
    return cos(angle) * speed, sin(angle) * speed


def load_map_from_csv(path_: str, int_: bool = True) -> list[list[int]]:
    """Load een 2D map van een csv bestand"""
    with open(path_, "r") as f:
        reader = csv.reader(f)
        return [[int(x) if int_ else x.lstrip() for x in line] for line in reader]


def write(
    anchor: str,
    content: str | int,
    font: pygame.Font,
    color: Color,
    x: int,
    y: int,
    alpha: int = 255,
    blit: bool = True,
    border: Optional[tuple[int, int, int]] = None,
    special_flags: int = 0,
    convert_to_tex: bool = True,
) -> tuple[Texture, pygame.Rect]:
    if border is not None:
        bc, bw = border, 1
        write(anchor, content, font, bc, x - bw, y - bw)
        write(anchor, content, font, bc, x + bw, y - bw)
        write(anchor, content, font, bc, x - bw, y + bw)
        write(anchor, content, font, bc, x + bw, y + bw)
    tex = font.render(str(content), True, color)
    if convert_to_tex:
        tex = Texture.from_surface(display.renderer, tex)
        tex.alpha = alpha
    else:
        tex.set_alpha(alpha)
    rect = tex.get_rect()

    setattr(rect, anchor, (int(x), int(y)))

    if blit:
        display.renderer.blit(tex, rect, special_flags=special_flags)

    return tex, rect


def borderize(
    img: pygame.Surface, color: tuple[int, int, int], thickness: int = 1
) -> pygame.Surface:
    """Returns a borderized version of a surface with the given color and thickness"""
    mask = pygame.mask.from_surface(img)
    mask_surf = mask.to_surface(setcolor=color)
    mask_surf.set_colorkey(Colors.BLACK)
    surf = pygame.Surface(
        [s + thickness * 2 for s in mask_surf.get_size()], pygame.SRCALPHA
    )
    poss = [[c * thickness for c in p] for p in [[1, 0], [2, 1], [1, 2], [0, 1]]]
    for pos in poss:
        surf.blit(mask_surf, pos)
    surf.blit(img, (thickness, thickness))
    return surf


def pi2pi(angle: float) -> float:
    """Normalize the angle in radians to 2 * pi"""
    return atan2(sin(angle), cos(angle))


def angle_diff(angle1: float, angle2: float) -> float:
    """Returns the smallest possible difference in given angles"""
    return min((angle1 - angle2 + 360) % 360, (angle2 - angle1 + 360) % 360)


cursor = Cursor()

client_udp: Client = None
client_tcp: Client = None

weapon_costs = {
    "1": 1200,
}
with open(Path("client", "assets", "weapon_data.json"), "r") as f:
    weapon_data = json.load(f)
weapon_names = [None] + [v["name"] for k, v in weapon_data.items()]

ticks = pygame.time.get_ticks


class Sounds:
    GUN = pygame.mixer.Sound(
        Path(
            "client",
            "assets",
            "sounds",
            "gun_sounds_2",
            "Full Sounds",
            ".308 (7.62x51)",
            "MP3",
            "308 Single.mp3",
        )
    )
    MAIN_MENU = pygame.mixer.Sound(
        Path("client", "assets", "sounds", "music", "tristram.mp3")
    )
    PLAY = pygame.mixer.Sound(Path("client", "assets", "sounds", "music", "doom.mp3"))
    FOOTSTEPS = {
        os.path.splitext(file_with_ext)[0]: pygame.mixer.Sound(
            Path("client", "assets", "sounds", "sfx", "footsteps", file_with_ext)
        )
        for file_with_ext in os.listdir(Path("client", "assets", "sounds", "sfx", "footsteps"))
    }


channel = pygame.mixer.Channel(0)
