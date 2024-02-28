import pygame
import sys

from math import sin, cos, tan, atan2, pi, radians, degrees, sqrt
from os import walk
from pathlib import Path
from pygame._sdl2.video import Window, Renderer, Texture, Image
from threading import Thread

from .include import *


class Game:
    def __init__(self):
        self.running = True
        self.stage = Stages.MAIN_MENU
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
        self.should_render_map = True

    def set_stage(self, stage):
        self.stage = stage

        if stage == Stages.PLAY:
            cursor.disable()
        else:
            cursor.enable()

    def render_map(self):
        for y, row in enumerate(self.map):
            for x, tile in enumerate(row):
                if tile == 0:
                    color = DARK_GRAY
                elif tile == 1:
                    color = RED
                fill_rect(
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
                WHITE,
                (0, y * self.tile_size),
                (self.map_width * self.tile_size, y * self.tile_size),
            )
        for x in range(self.map_width):
            draw_line(
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

    def draw(self):
        draw_rect(self.color, (self.rect.x, self.rect.y, self.w, self.h))

    def keys(self):
        if game.stage == Stages.PLAY:
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
        if game.should_render_map:
            draw_line(BLACK, p1, p2)

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
                [wh / display.height * 255] * 3 + [255],
                (wx, wy, ww, wh),
            )
            if game.should_render_map:
                # raying the 2D rays
                draw_line(GREEN, p1, p2)

    def update(self):
        self.keys()
        if game.should_render_map:
            self.draw()


cursor.enable()
game = Game()
player = Player()
clock = pygame.time.Clock()

buttons = [
    Button(
        48,
        display.height / 2,
        300,
        50,
        "Unleash PANDEMONIUM",
        lambda: game.set_stage(Stages.PLAY),
    )
]

black_square = pygame.Surface((display.width, display.height), pygame.SRCALPHA)
black_square.fill(BLACK)
black_square.set_alpha(40)
black_square = Texture.from_surface(display.renderer, black_square)
black_square_rect = black_square.get_rect()


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
            match event.type:
                case pygame.QUIT:
                    game.running = False
                case pygame.MOUSEMOTION:
                    if pygame.mouse.get_pos()[0] > display.width - 20:
                        pygame.mouse.set_pos(20, pygame.mouse.get_pos()[1])
                    elif pygame.mouse.get_pos()[0] < 20:
                        pygame.mouse.set_pos(
                            display.width - 20, pygame.mouse.get_pos()[1]
                        )
                    else:
                        player.angle += event.rel[0] * game.sens
                        player.angle %= 2 * pi
                case pygame.MOUSEBUTTONDOWN:
                    for button in buttons:
                        if button.rect.colliderect(cursor.rect):
                            button.action()
                case pygame.KEYDOWN:
                    match event.key:
                        case pygame.K_ESCAPE:
                            if game.stage == Stages.SETTINGS:
                                game.stage = Stages.PLAY
                            elif game.stage == Stages.PLAY:
                                game.stage = Stages.SETTINGS

        display.renderer.clear()

        if game.stage in (Stages.MAIN_MENU, Stages.SETTINGS):
            for button in buttons:
                button.update()

            cursor.update()

        match game.stage:
            case Stages.MAIN_MENU:
                display.renderer.blit(black_square, black_square_rect)
                write(
                    "center",
                    "PANDEMONIUM",
                    v_fonts[100],
                    WHITE,
                    int(display.width / 2),
                    150,
                )
            case Stages.PLAY:
                fill_rect(
                    DARK_GRAY,
                    (0, 0, display.width, display.height / 2),
                )
                fill_rect(
                    BROWN,
                    (0, display.height / 2, display.width, display.height / 2),
                )
                if game.should_render_map:
                    game.render_map()
                player.update()
            case Stages.SETTINGS:
                pass

        display.renderer.present()

    pygame.quit()
    sys.exit()
