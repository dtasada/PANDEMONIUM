import pygame
import sys
import json

from math import sin, cos, tan, atan2, pi, radians, degrees, sqrt
from pathlib import Path
from pygame._sdl2.video import Window, Renderer, Texture, Image
from threading import Thread

from .include import *


class Game:
    def __init__(self):
        # misc.
        self.running = True
        self.state = self.previous_state = States.MAIN_MENU
        self.fps = 60
        self.sens = 50
        self.fov = 60
        self.ray_density, self.resolution = 1280 // 4, 5 # Don't change this pair ['§ok ±boomer}
        self.target_zoom = self.zoom = 0
        self.zoom_speed = 0.4
        # map
        self.map = load_map_from_csv(Path("client", "assets", "map.csv"))
        self.object_map = load_map_from_csv(
            Path("client", "assets", "object_map.csv"), int_=False
        )
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
        self.map_surf = pygame.Surface(
            (self.map_width * self.tile_size, self.map_height * self.tile_size),
            pygame.SRCALPHA,
        )
        for y, row in enumerate(self.map):
            for x, tile in enumerate(row):
                img = self.tiles[tile]
                self.map_surf.blit(img, (x * self.tile_size, y * self.tile_size))
        self.map_tex = Texture.from_surface(display.renderer, self.map_surf)
        self.mo = self.tile_size * 1  # map offset!!!!!!!!!!
        self.map_rect = self.map_tex.get_rect(topleft=(self.mo, self.mo))

    @property
    def rect_list(self):
        return sum(self.rects, [])

    def set_state(self, state):
        self.previous_state = self.state
        self.state = state

        global current_buttons
        current_buttons = all_buttons[self.state]
        if state == States.PLAY:
            cursor.disable()
        else:
            cursor.enable()

    def get_fov(self):
        return self.fov

    def set_fov(self, amount):
        self.fov += amount

        if self.fov > 120:
            self.fov = 120
        if self.fov < 30:
            self.fov = 30

    def get_sens(self):
        return self.sens

    def set_sens(self, amount):
        self.sens += amount

    def get_res(self):
        return self.resolution

    def set_res(self, amount):
        resolutions = [80, 160, 320, 640, 1280]
        self.resolution += amount
        if self.resolution > 5:
            self.resolution = 5
        elif self.resolution < 1:
            self.resolution = 1

        self.ray_density = resolutions[self.resolution - 1]


class Player:
    def __init__(self):
        self.x = game.tile_size * 8
        self.y = game.tile_size * 8
        self.w = 8
        self.h = 8
        self.color = Colors.WHITE
        self.angle = -1.5708
        self.arrow_img = Image(imgload(
            "client", "assets", "images", "player_arrow.png", scale=1
        ))
        self.arrow_rect = pygame.Rect(0, 0, 16, 16)
        self.rect = pygame.FRect((self.x, self.y, self.w, self.h))
        self.weapons = {}
        self.wall_textures = [
            (
                Texture.from_surface(
                    display.renderer,
                    pygame.transform.scale_by(
                        pygame.image.load(
                            Path("client", "assets", "images", file_name + ".png")
                        ),
                        0.25,
                    ),
                )
                if file_name is not None
                else None
            )
            for file_name in [None, "wall"]
        ]
        self.object_textures = [
            (
                imgload("client", "assets", "images", file_name + ".png")
                if file_name is not None
                else None
            )
            for file_name in [None, "ak"]
        ]
        self.highlighted_object_textures = [
            (
                Texture.from_surface(
                    display.renderer,
                    borderize(
                        pygame.image.load(
                            Path("client", "assets", "images", file_name + ".png")
                        ),
                        Colors.YELLOW,
                    ),
                )
                if file_name is not None
                else None
            )
            for file_name in [None, "ak"]
        ]
        self.mask_object_textures = []
        for file_name in [None, "ak"]:
            if file_name is None:
                tex = None
            else:
                surf = pygame.mask.from_surface(
                    pygame.image.load(
                        Path("client", "assets", "images", file_name + ".png")
                    )
                ).to_surface(setcolor=Colors.WHITE)
                surf.set_colorkey(Colors.BLACK)
                tex = Texture.from_surface(display.renderer, surf)
            self.mask_object_textures.append(tex)
        self.bob = 0
        self.to_equip = None
        # weapon
        self.weapon_tex = self.weapon_rect = None

    @property
    def health(self):
        # TODO: Server call
        return 100

    def draw(self):
        self.arrow_rect.center = self.rect.center
        self.arrow_img.angle = degrees(self.angle)
        display.renderer.blit(self.arrow_img, pygame.Rect(self.arrow_rect.x + game.mo, self.arrow_rect.y + game.mo, *self.arrow_rect.size))
        # draw_rect(Colors.GREEN, self.rect)
        if self.to_equip is not None:
            coord, obj = self.to_equip
            cost = weapon_costs[obj[0]]
            write(
                "midbottom",
                f"Press <e> to buy for ${cost}",
                v_fonts[52],
                Colors.WHITE,
                display.width / 2,
                display.height - 50,
            )
            if joystick is not None:
                joystick_button_rect.midbottom = (display.width / 2 - 115, display.height - 42)
                display.renderer.blit(joystick_button_sprs[Joymap.SQUARE], joystick_button_rect)
        if self.weapon_tex is not None:
            display.renderer.blit(self.weapon_tex, self.weapon_rect)

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
    
    def try_to_buy_wall_weapon(self):
        if self.to_equip is not None:
            (x, y), obj = self.to_equip
            x, y = int(x), int(y)
            game.object_map[y][x] = "0"
            weapon = obj[0]
            self.set_weapon(weapon)

    def keys(self):
        # keyboard
        self.to_equip = None
        self.surround = []
        if game.state == States.PLAY:
            # keyboard
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

            # joystick isn't actually a literal joystick, pygame input term for gamepad
            if joystick is not None:
                # movement
                thr = 0.06
                ax0 = joystick.get_axis(0)
                ax1 = joystick.get_axis(1)
                if abs(ax0) <= thr:
                    ax0 = 0
                if abs(ax1) <= thr:
                    ax1 = 0
                theta = pi2pi(player.angle) + 0.5 * pi
                ax0p = ax0 * cos(theta) - ax1 * sin(theta)
                ax1p = ax0 * sin(theta) + ax1 * cos(theta)
                thr = 0.06
                # sprint mechanics
                if joystick.get_button(Joymap.LEFT_JOYSTICK_CLICK):
                    sprint_m = 2
                    ax0p *= sprint_m
                    ax1p *= sprint_m
                if ax0p != 0 or ax1p != 0:
                    xvel, yvel = ax0p * vmult, ax1p * vmult
                # rotation
                m = 0.0008 * game.sens
                ax2 = joystick.get_axis(Joymap.LEFT_JOYSTICK)
                ax3 = joystick.get_axis(Joymap.RIGHT_JOYSTICK)
                if abs(ax2) <= thr:
                    ax2 = 0
                if abs(ax3) <= thr:
                    ax3 = 0
                rot_xvel = ax2 * m
                # rot_yvel = ax3 * m
                self.angle += rot_xvel

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

        # for rays
        self.start_x = (self.rect.centerx + cos(self.angle) * game.zoom) / game.tile_size
        self.start_y = (self.rect.centery + sin(self.angle) * game.zoom) / game.tile_size

        # surroundings
        tile_x = int(self.rect.x / game.tile_size)
        tile_y = int(self.rect.y / game.tile_size)
        o = 1
        for yo in range(-o, o + 1):
            for xo in range(-o, o + 1):
                x = tile_x + xo
                y = tile_y + yo
                self.surround.append((x, y))

        # cast the rays
        if game.target_zoom > 0:
            start_x, start_y = self.rect.centerx / game.tile_size, self.rect.centery / game.tile_size
            self.cast_ray(0, 0, start_x, start_y)
        else:
            o = -game.fov // 2
            for index in range(game.ray_density):
                o += game.fov / game.ray_density
                self.cast_ray(o, index)
        _xvel, _yvel = angle_to_vel(self.angle)

        # processing other important joystick input
        if joystick is not None:
            if joystick.get_button(Joymap.SQUARE):
                self.try_to_buy_wall_weapon()

    def cast_ray(self, deg_offset, index, start_x=None, start_y=None):  # add comments here pls
        offset = radians(deg_offset)
        angle = self.angle + offset
        dx = cos(angle)
        dy = sin(angle)

        tot_length = 0
        y_length = x_length = 0
        start_x = start_x if start_x is not None else self.start_x
        start_y = start_y if start_y is not None else self.start_y
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
            # object (wall weapon)
            obj = game.object_map[cur_y][cur_x]
            # general ray calculations (big branin)
            p1 = (start_x * game.tile_size, start_y * game.tile_size)
            p2 = (
                p1[0] + dist * dx * game.tile_size,
                p1[1] + dist * dy * game.tile_size,
            )
            self.rays.append((p1, p2))
            ray_mult = 1
            # init vars for walls
            dist *= ray_mult
            dist_px = dist * game.tile_size
            ww = display.width / game.ray_density
            wh = display.height * game.tile_size / dist_px * 1.7
            wx = index * ww
            wy = display.height / 2 - wh / 2 + self.bob
            # texture calculations
            cur_pix_x = cur_x * game.tile_size
            cur_pix_y = cur_y * game.tile_size
            tex_dx = round(p2[0] - cur_pix_x, 2)
            tex_dy = round(p2[1] - cur_pix_y, 2)
            if tex_dx == 0:
                # col left, so hit - tile
                tex_d = p2[1] - cur_pix_y
                orien = 3  # left
            elif tex_dx == game.tile_size:
                # col right, so tile - hit
                tex_d = p2[1] - cur_pix_y
                orien = 1  # right
            elif tex_dy == 0:
                # col top, so size - (hit - tile)
                tex_d = game.tile_size - (p2[0] - cur_pix_x)
                orien = 0  # top
            elif tex_dy == game.tile_size:
                # col bottom, so hit - tile
                tex_d = p2[0] - cur_pix_x
                orien = 2  # bottom
            # fill_rect(
            #     [int(min(wh / display.height * 255, 255))] * 3 + [255],
            #     pygame.FRect(wx, wy, ww, wh),
            # )

            # Texture rendering
            tex = self.wall_textures[tile_value]
            axo = tex_d / game.tile_size * tex.width
            tex.color = [int(min(wh * 2 / display.height * 255, 255))] * 3
            display.renderer.blit(
                tex,
                pygame.Rect(wx, wy, ww, wh),
                pygame.Rect(axo, 0, 1, tex.height),
            )
            # check whether the wall weapon is in the correct orientation
            if len(obj) > 1:
                if int(obj[1]) == orien:
                    high = (cur_x, cur_y) in self.surround
                    if high:
                        lookup = self.highlighted_object_textures
                        self.to_equip = ((cur_x, cur_y), obj)
                    else:
                        lookup = self.object_textures
                    tex = lookup[int(obj[0])]
                    display.renderer.blit(
                        tex,
                        pygame.Rect(wx, wy, ww, wh),
                        pygame.Rect(axo + high, 0, 1, tex.height),
                    )
            self.render_map()

    def send_location(self):
        data = {"x": self.arrow_rect.x + game.mo, "y": self.arrow_rect.y + game.mo, "angle": self.angle}
        data = json.dumps(data)
        client_udp.req(data)

    def set_weapon(self, weapon):
        weapon = int(weapon)
        self.weapon_tex = self.mask_object_textures[weapon]
        self.weapon_rect = self.weapon_tex.get_rect(
            bottomright=(display.width - 140, display.height - 10)
        ).scale_by(4)
        self.weapons[weapon] = 100

    def update(self):
        self.rays = []
        self.keys()
        hud.health_update(self.health, False)
        hud.ammo_update(self.health, False)
        # Thread(client_tcp.req, args=(self.health,)).start()
        for ray in self.rays:
            p1 = (ray[0][0] + game.mo, ray[0][1] + game.mo)
            p2 = (ray[1][0] + game.mo, ray[1][1] + game.mo)
            draw_line(Colors.GREEN, p1, p2)

class EnemyPlayer:
    def __init__(self, id_):
        self.id_ = id_
        self.x = game.tile_size * 8
        self.y = game.tile_size * 8
        self.w = 8
        self.h = 8
        self.angle = -1.5708
        self.arrow_surf = pygame.image.load(
            Path("client", "assets", "images", "player_arrow.png")
        )
        self.rect = pygame.FRect((self.x, self.y, self.w, self.h))
        self.arrow_img = Image(Texture.from_surface(display.renderer, self.arrow_surf))
        self.indicator_img = imgload("client", "assets", "images", "enemy_indicator.png")
        self.indicator_rect = self.indicator_img.get_rect()

    def draw(self):
        arrow_rect = pygame.Rect(*self.rect.topleft, 16, 16)
        arrow = self.arrow_img
        arrow.angle = degrees(self.angle)
        draw_rect(Colors.GREEN, arrow_rect)
        # display.renderer.blit(arrow, pygame.Rect(arrow_rect.x, arrow_rect.y, *arrow_rect.size))
        display.renderer.blit(self.indicator_img, pygame.Rect(arrow_rect.x, arrow_rect.y, *arrow_rect.size))

    def update(self):
        if client_udp.current_message:
            if self.id_ not in client_udp.current_message:
                enemy_players.remove(self)
                return
            message = json.loads(client_udp.current_message)
            self.rect.x = message[self.id_]["x"]
            self.rect.y = message[self.id_]["y"]
            self.angle = message[self.id_]["angle"]
        dist = hypot(
            self.rect.centerx - player.rect.centerx,
            self.rect.centery - player.rect.centery
        )
        self.draw()


cursor.enable()
game = Game()
player = Player()
enemy_players = []
hud = HUD()
clock = pygame.time.Clock()
joystick = None

crosshair_tex = imgload("client", "assets", "images", "crosshair.png", scale=3)
crosshair_rect = crosshair_tex.get_rect(center=(display.center))

title = Button(
    int(display.width / 2),
    150,
    "PANDEMONIUM",
    None,
    font_size=96,
    anchor="center",
)

main_settings_buttons = [
    title,
    Button(
        80,
        display.height / 2 + 48 * 0,
        "Field of view",
        game.set_fov,
        action_arg=10,
        is_slider=True,
        slider_display=game.get_fov,
    ),
    Button(
        80,
        display.height / 2 + 48 * 1,
        "Sensitivity",
        game.set_sens,
        action_arg=10,
        is_slider=True,
        slider_display=game.get_sens,
    ),
    Button(
        80,
        display.height / 2 + 48 * 2,
        "Resolution",
        game.set_res,
        action_arg=1,
        is_slider=True,
        slider_display=game.get_res,
    ),
    Button(
        80,
        display.height / 2 + 48 * 3,
        "Back",
        lambda: game.set_state(game.previous_state),
        font_size=48,
    ),
]

all_buttons = {
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
            lambda: game.set_state(States.MAIN_SETTINGS),
        ),
    ],
    States.MAIN_SETTINGS: main_settings_buttons,
    States.PLAY_SETTINGS: [
        *main_settings_buttons[0:4],
        Button(
            80,
            display.height / 2 + 48 * 3,
            "Return to main menu",
            lambda: game.set_state(States.MAIN_MENU),
        ),
        Button(
            80,
            display.height / 2 + 48 * 4,
            "Back",
            lambda: game.set_state(game.previous_state),
            font_size=48,
        ),
    ],
    States.PLAY: []
}

game.set_state(States.MAIN_MENU)


class Hue:
    def __init__(self, color, alpha):
        self.surf = pygame.Surface((display.width, display.height), pygame.SRCALPHA)
        self.surf.fill(color)
        self.surf.set_alpha(alpha)
        self.tex = Texture.from_surface(display.renderer, self.surf)
        self.rect = self.surf.get_rect()


darken_game = Hue(Colors.BLACK, 80)
redden_game = Hue(Colors.RED, 20)


floor_tex = imgload("client", "assets", "images", "floor.jpg")
joystick_button_sprs = imgload("client", "assets", "images", "buttons.png", scale=4, frames=4)
joystick_button_rect = joystick_button_sprs[0].get_rect()


def check_new_players():
    if client_udp.current_message:
        message = json.loads(client_udp.current_message)
        for addr in message:
            if EnemyPlayer(addr) not in enemy_players:
                enemy_players.append(EnemyPlayer(addr))


def render_floor():
    fill_rect(
        Colors.BROWN,
        (
            0,
            display.height / 2 + player.bob,
            display.width,
            display.height / 2 - player.bob,
        ),
    )


def main(multiplayer):
    global client_udp, client_tcp, joystick

    if multiplayer:
        client_udp = Client("udp")
        client_tcp = Client("tcp")
        Thread(target=client_udp.receive, daemon=True).start()
        Thread(target=client_tcp.receive, daemon=True).start()

    while game.running:
        clock.tick(game.fps)
        for event in pygame.event.get():
            match event.type:
                case pygame.QUIT:
                    game.running = False
                    if multiplayer:
                        client_udp.req("quit")
                        pygame.quit()
                        sys.exit()

                case pygame.MOUSEMOTION:
                    if cursor.should_wrap:
                        if game.state == States.PLAY:
                            xpos = pygame.mouse.get_pos()[0]
                            ypos = pygame.mouse.get_pos()[1]

                            # if/elif are for horizontal mouse wrap
                            if xpos > display.width - 20:
                                pygame.mouse.set_pos(20, ypos)
                            elif xpos < 20:
                                pygame.mouse.set_pos(display.width - 21, ypos)
                            else:
                                player.angle += event.rel[0] * game.sens / 100_000
                                player.angle %= 2 * pi

                            # if/elif are for vertical mouse wrap
                            if ypos > display.height - 20:
                                pygame.mouse.set_pos(xpos, 20)
                            elif ypos < 20:
                                pygame.mouse.set_pos(xpos, display.height - 21)
                            else:
                                player.bob -= event.rel[1]

                case pygame.MOUSEBUTTONDOWN:
                    if game.state == States.PLAY:
                        if event.button == 1:
                            game.target_zoom = 30
                            game.zoom = 0

                case pygame.MOUSEBUTTONUP:
                    if game.state == States.PLAY:
                        if event.button == 1:
                            game.target_zoom = 0

                case pygame.KEYDOWN:
                    match event.key:
                        case pygame.K_ESCAPE:
                            match game.state:
                                case States.PLAY_SETTINGS:
                                    game.set_state(States.PLAY)
                                case States.PLAY:
                                    game.set_state(States.PLAY_SETTINGS)

                        case pygame.K_e:
                            player.try_to_buy_wall_weapon()

                case pygame.JOYDEVICEADDED:
                    joystick = pygame.joystick.Joystick(event.device_index)

            for button_list in all_buttons.values():
                for button in button_list:
                    button.process_event(event)

        display.renderer.clear()

        # blit
        if game.state == States.MAIN_MENU:
            fill_rect(Colors.BLACK, (0, 0, display.width, display.height))
        else:
            if multiplayer:
                player.send_location()

            if game.state in (States.PLAY, States.PLAY_SETTINGS):
                fill_rect(
                    Colors.DARK_GRAY,
                    (0, 0, display.width, display.height / 2 + player.bob),
                )
                fill_rect(
                    Colors.BROWN,
                    (
                        0,
                        display.height / 2 + player.bob,
                        display.width,
                        display.height / 2 - player.bob,
                    ),
                )

                player.update()
                if game.should_render_map:
                    player.draw()
                    if multiplayer:
                        check_new_players()
                        for enemy in enemy_players:
                            enemy.update()

            display.renderer.blit(crosshair_tex, crosshair_rect)
            display.renderer.blit(redden_game.tex, redden_game.rect)

            if game.state == States.PLAY:
                # zoom
                game.zoom += (game.target_zoom - game.zoom) * game.zoom_speed

                display.renderer.blit(crosshair_tex, crosshair_rect)

        if game.state == States.MAIN_SETTINGS:
            fill_rect((0, 0, 0, 255), (0, 0, display.width, display.height))
        elif game.state == States.PLAY_SETTINGS:
            display.renderer.blit(darken_game.tex, darken_game.rect)

        for button in current_buttons:
            button.update()

        if cursor.enabled:
            cursor.update()

        write(
            "topright",
            str(int(clock.get_fps())),
            v_fonts[20],
            Colors.WHITE,
            display.width - 5,
            5,
        )

        display.renderer.present()

    pygame.quit()
    sys.exit()
