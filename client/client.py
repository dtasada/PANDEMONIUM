import pygame
import sys

from math import sin, cos, tan, atan2, pi, radians, degrees, sqrt
from os import walk
from pathlib import Path
from pygame._sdl2.video import Window, Renderer, Texture, Image
from threading import Thread
from pprint import pprint

from .include import *


class Game:
    def __init__(self):
        # misc.
        self.running = True
        self.state = self.previous_state = States.MAIN_MENU
        self.fps = 60
        self.sens = 0.0005
        self.fov = 60
        self.num_rays = 320
        # map
        self.map = load_map_from_csv(Path("client", "assets", "map.csv"))
        self.tile_size = 16
        self.map_height = len(self.map)
        self.map_width = len(self.map[0])
        self.rects = [
            [
                (
                    pygame.Rect(
                        x * self.tile_size,
                        y * self.tile_size,
                        self.tile_size,
                        self.tile_size,
                    )
                    if self.map[y][x] != 0
                    else None
                )
                for x in range(self.map_width)
            ]
            for y in range(self.map_height)
        ]
        self.draw_rects = [
            [
                pygame.Rect(
                    x * self.tile_size,
                    y * self.tile_size,
                    self.tile_size,
                    self.tile_size,
                )
                for x in range(self.map_width)
            ]
            for y in range(self.map_height)
        ]

        # misc.
        self.should_render_map = True
        self.debug_map = False
        self.tiles = [
            pygame.transform.scale_by(
                pygame.image.load(Path("client", "assets", "images", file_name)),
                self.tile_size / 16,
            )
            for file_name in ["floor.png", "floor_wall.png"]
        ]
        self.map_surf = pygame.Surface((self.map_width * self.tile_size, self.map_height * self.tile_size), pygame.SRCALPHA)
        for y, row in enumerate(self.map):
            for x, tile in enumerate(row):
                img = self.tiles[tile]
                self.map_surf.blit(img, (x * self.tile_size, y * self.tile_size))
        self.map_tex = Texture.from_surface(display.renderer, self.map_surf)
        self.map_rect = self.map_tex.get_rect()

    @property
    def rect_list(self):
        return sum(self.rects, [])

    def set_state(self, state):
        self.previous_state = self.state
        self.state = state

        global buttons
        buttons = button_lists[self.state]

        if state == States.PLAY:
            cursor.disable()
        else:
            cursor.enable()


class Player:
    def __init__(self):
        self.x = game.tile_size * 8
        self.y = game.tile_size * 8
        self.w = 8
        self.h = 8
        self.color = Colors.WHITE
        self.angle = -1.5708

        self.arrow_surf = pygame.image.load(
            Path("client", "assets", "images", "arrow.png")
        )
        self.rect = pygame.FRect((self.x, self.y, self.w, self.h))
        self.arrow_img = Image(Texture.from_surface(display.renderer, self.arrow_surf))

        self.wall_textures = [
            (
                Texture.from_surface(
                    display.renderer,
                    pygame.image.load(Path("client", "assets", "images", file_name)),
                )
                if file_name is not None
                else None
            )
            for file_name in [None, "wall.png"]
        ]

    @property
    def health(self):
        # TODO: Server call
        return 100

    def draw(self):
        self.arrow_img.angle = degrees(self.angle)
        arrow_rect = pygame.Rect(*self.rect.topleft, 16, 16)
        arrow_rect.center = self.rect.center
        display.renderer.blit(self.arrow_img, arrow_rect)
        # draw_rect(Colors.GREEN, self.rect)

    def render_map(self):
        display.renderer.blit(game.map_tex, game.map_rect)

        if game.debug_map:
            for y in range(game.map_height):
                draw_line(
                    Colors.WHITE,
                    (game.tile_size, (y + 1) * self.tile_size),
                    ((game.map_width + 1) * game.tile_size, (y + 1) * self.tile_size),
                )
            for x in range(game.map_width):
                draw_line(
                    Colors.WHITE,
                    ((x + 1) * game.tile_size, game.tile_size),
                    ((x + 1) * game.tile_size, (game.map_height + 1) * game.tile_size),
                )

    def keys(self):
        if game.state == States.PLAY:
            vmult = 0.8
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
            for rect in game.rect_list:
                if rect is not None and self.rect.colliderect(rect):
                    if xvel >= 0:
                        self.rect.right = rect.left
                    else:
                        self.rect.left = rect.right
            self.rect.y += yvel
            for rect in game.rect_list:
                if rect is not None and self.rect.colliderect(rect):
                    if yvel >= 0:
                        self.rect.bottom = rect.top
                    else:
                        self.rect.top = rect.bottom

        o = -game.fov // 2
        for index in range(game.num_rays):
            o += game.fov / game.num_rays
            self.cast_ray(o, index)
        # self.cast_ray(0, 0)
        _xvel, _yvel = angle_to_vel(self.angle)
        m = 20
        p1 = self.rect.center
        p2 = (self.rect.centerx + _xvel * m, self.rect.centery + _yvel * m)

    def cast_ray(self, deg_offset, index):  # add comments here pls
        offset = radians(deg_offset)
        angle = self.angle + offset
        dx = cos(angle)
        dy = sin(angle)

        tot_length = 0
        y_length = x_length = 0
        start_x, start_y = [
            self.rect.centerx / game.tile_size,
            self.rect.centery / game.tile_size,
        ]
        cur_x, cur_y = [int(start_x), int(start_y)]
        hypot_x, hypot_y = sqrt(1 + (dy / dx) ** 2), sqrt(1 + (dx / dy) ** 2)
        direc = (dx, dy)

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
            tile_value = game.map[cur_y][cur_x]
            if tile_value != 0:
                col = True
        if col:
            # general ray calculations
            p1 = (start_x * game.tile_size, start_y * game.tile_size)
            p2 = (
                p1[0] + dist * dx * game.tile_size,
                p1[1] + dist * dy * game.tile_size,
            )
            self.rays.append((p1, p2))
            ray_mult = 1
            # init vars for wallss
            dist *= ray_mult
            dist_px = dist * game.tile_size
            wh = display.height * game.tile_size / dist_px
            ww = display.width / game.num_rays
            wx = index * ww
            wy = display.height / 2 - wh / 2
            # texture calculations
            cur_pix_x = cur_x * game.tile_size
            cur_pix_y = cur_y * game.tile_size
            tex_dx = round(p2[0] - cur_pix_x, 2)
            tex_dy = round(p2[1] - cur_pix_y, 2)
            if tex_dx == 0:
                # col left, so hit - tile
                tex_d = p2[1] - cur_pix_y
            elif tex_dx == game.tile_size:
                # col right, so tile - hit
                tex_d = p2[1] - cur_pix_y
            elif tex_dy == 0:
                # col top, so size - (hit - tile)
                tex_d = game.tile_size - (p2[0] - cur_pix_x)
            elif tex_dy == game.tile_size:
                # col bottom, so hit - tile
                tex_d = p2[0] - cur_pix_x
            # fill_rect(
            #     [int(min(wh / display.height * 255, 255))] * 3 + [255],
            #     pygame.FRect(wx, wy, ww, wh),
            # )
            tex = self.wall_textures[tile_value]
            axo = tex_d / game.tile_size * tex.width
            tex.color = [int(min(wh * 2 / display.height * 255, 255))] * 3
            display.renderer.blit(
                tex,
                pygame.Rect(wx, wy, ww, wh),
                pygame.Rect(axo, 0, 1, tex.height),
            )

            self.render_map()

    def update(self):
        self.rays = []
        self.keys()
        hud.health_update(self.health, False)
        hud.ammo_update(self.health, False)
        # Thread(client_tcp.req, args=(self.health,)).start()
        for ray in self.rays:
            draw_line(Colors.GREEN, *ray)

cursor.enable()
game = Game()
player = Player()
hud = HUD()
clock = pygame.time.Clock()

crosshair_tex = timgload3("client", "assets", "images", "crosshair.png")
crosshair_rect = crosshair_tex.get_rect(center=(display.center))

title = Button(
    int(display.width / 2),
    150,
    "PANDEMONIUM",
    None,
    font_size=96,
    anchor="center",
)

button_lists = {
    States.MAIN_MENU: [
        title,
        Button(
            80,
            display.height / 2 + 48 * 0,
            "Unleash PANDEMONIUM",
            lambda: game.set_state(States.PLAY),
            font_size=48,
            color=Colors.RED,
        ),
        Button(
            80,
            display.height / 2 + 48 * 1,
            "Settings",
            lambda: game.set_state(States.SETTINGS),
        ),
    ],
    States.SETTINGS: [
        title,
        Button(
            80,
            display.height / 2 + 48 * 0,
            "Field of view",
            None,
        ),
        Button(
            80,
            display.height / 2 + 48 * 1,
            "Sensitivity",
            None,
        ),
        Button(
            80,
            display.height / 2 + 48 * 2,
            "Resolution",
            None,
        ),
        Button(
            80,
            display.height / 2 + 48 * 3,
            "Back",
            lambda: game.set_state(game.previous_state),
            font_size=48,
        ),
    ],
    States.PLAY: [],
}

buttons = button_lists[States.MAIN_MENU]


class DarkenGame:
    def __init__(self):
        self.surf = pygame.Surface((display.width, display.height), pygame.SRCALPHA)
        self.surf.fill(Colors.BLACK)
        self.surf.set_alpha(40)
        self.tex = Texture.from_surface(display.renderer, self.surf)
        self.rect = self.surf.get_rect()


darken_game = DarkenGame()


def main(multiplayer):
    global client_udp, client_tcp

    if multiplayer:
        client_udp = Client("udp")
        client_tcp = Client("tcp")
        Thread(target=client_udp.receive, daemon=True).start()
        Thread(target=client_tcp.receive, daemon=True).start()

    while game.running:
        clock.tick(game.fps)
        for event in pygame.event.get():
            for button_list in button_lists.values():
                for button in button_list:
                    button.process_event(event)
            match event.type:
                case pygame.QUIT:
                    game.running = False

                case pygame.MOUSEMOTION:
                    if cursor.should_wrap:
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
                    pass

                case pygame.KEYDOWN:
                    match event.key:
                        case pygame.K_ESCAPE:
                            match game.state:
                                case States.SETTINGS:
                                    game.set_state(States.PLAY)
                                case States.PLAY:
                                    game.set_state(States.SETTINGS)

        display.renderer.clear()

        # blit
        if game.state == States.MAIN_MENU:
            fill_rect(Colors.BLACK, (0, 0, display.width, display.height))

        if game.state == States.PLAY:
            fill_rect(
                Colors.DARK_GRAY,
                (0, 0, display.width, display.height / 2),
            )
            fill_rect(
                Colors.BROWN,
                (0, display.height / 2, display.width, display.height / 2),
            )

            player.update()
            display.renderer.blit(crosshair_tex, crosshair_rect)

            if game.should_render_map:
                player.draw()

        if game.state == States.SETTINGS:
            if game.previous_state == States.MAIN_MENU:
                fill_rect((0, 0, 0, 255), (0, 0, display.width, display.height))
            else:
                display.renderer.blit(darken_game.tex, darken_game.rect)

        for button in buttons:
            button.update()

        if cursor.enabled:
            cursor.update()

        write("topleft", str(int(clock.get_fps())), v_fonts[20], Colors.WHITE, 5, 5)

        display.renderer.present()

    pygame.quit()
    sys.exit()
