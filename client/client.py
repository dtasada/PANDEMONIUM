import pygame
import sys
import json
import os

from math import sin, cos, tan, atan2, pi, radians, degrees, sqrt, hypot
from pathlib import Path
from pygame._sdl2.video import Texture, Image
from threading import Thread
from random import randint as rand

from .include import *
import atexit


def quit():
    json_save = {
        "resolution": game.resolution,
        "fov": game.fov,
        "sens": game.sens,
    }
    with open(Path("client", "settings.json"), "w") as f:
        json.dump(json_save, f)

    if game.multiplayer and client_tcp:
        client_tcp.req("quit")

    game.running = False
    print("Exited successfully")
    pygame.quit()


atexit.register(quit)


class Game:
    def __init__(self):
        # settings values
        try:
            if os.path.isfile(Path("client", "settings.json")):
                with open(Path("client", "settings.json"), "r") as f:
                    json_load = json.load(f)
                    self.sens = json_load["sens"]
                    self.fov = json_load["fov"]
                    self.resolution = json_load["resolution"]
            else:
                open(Path("client", "settings.json"), "w").close()
                self.sens = 50
                self.fov = 60
                self.resolution = 2
        except:
            self.sens = 50
            self.fov = 60
            self.resolution = 2

        self.ray_density = int(display.width * (self.resolution / 4))
        self.resolutions_list = [
            int(display.width * coef) for coef in [0.125, 0.25, 0.5, 1.0]
        ]
        # misc.
        self.running = True
        self.multiplayer = None
        self.state = States.MAIN_MENU
        self.previous_state = States.LAUNCH
        self.fps = 60
        
        self.target_zoom = self.zoom = 0
        self.zoom_speed = 0.4
        self.projection_dist = 32 / tan(radians(self.fov / 2))
        self.rendered_enemies = 0
        # map
        self.maps = {}
        for file in os.listdir(Path("client", "assets", "maps")):
            file_name = file.split("-")[0]
            self.maps[file_name] = {
                "walls": load_map_from_csv(
                    Path("client", "assets", "maps", f"{file_name}-walls.csv")
                ),
                "weapons": load_map_from_csv(
                    Path("client", "assets", "maps", f"{file_name}-weapons.csv"),
                    int_=False,
                ),
            }

        self.current_map = self.maps["strike"]["walls"]
        self.current_object_map = self.maps["strike"]["weapons"]

        self.tile_size = 16
        self.map_height = len(self.current_map)
        self.map_width = len(self.current_map[0])
        self.rects = [
            [
                (
                    pygame.Rect(
                        x * self.tile_size,
                        y * self.tile_size,
                        self.tile_size,
                        self.tile_size,
                    )
                    if self.current_map[y][x] != 0
                    else None
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
                pygame.image.load(
                    Path("client", "assets", "images", "minimap", file_name)
                ),
                self.tile_size / 16,
            )
            for file_name in ["floor.png", "floor_wall.png"]
        ]
        self.map_surf = pygame.Surface(
            (self.map_width * self.tile_size, self.map_height * self.tile_size),
            pygame.SRCALPHA,
        )
        for y, row in enumerate(self.current_map):
            for x, tile in enumerate(row):
                img = self.tiles[tile]
                self.map_surf.blit(img, (x * self.tile_size, y * self.tile_size))
        self.map_tex = Texture.from_surface(display.renderer, self.map_surf)
        self.mo = self.tile_size * 0
        self.map_rect = self.map_tex.get_rect(topleft=(self.mo, self.mo))

    @property
    def rect_list(self):
        return sum(self.rects, [])

    def stop_running(self):
        self.running = False

    def set_state(self, state):
        global player

        if self.previous_state == States.LAUNCH or state == States.MAIN_MENU:
            player = Player()

            # All launch & init requirements
            msg = json.dumps({
                'health': player.health,
                'color': player_selector.prim_color,
                'name': username_input.text,
            })
            client_tcp.req(f"init_player|{player.tcp_id}|{msg}")

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
        self.fov = min(self.fov, 120)
        self.fov = max(self.fov, 30)

    def get_sens(self):
        return self.sens

    def set_sens(self, amount):
        self.sens += amount
        self.sens = max(self.sens, 10)

    def get_res(self):
        return self.resolution

    def set_res(self, amount):
        self.resolution += amount
        self.resolution = min(self.resolution, 4)
        self.resolution = max(self.resolution, 1)

        self.ray_density = self.resolutions_list[self.resolution - 1]


class GlobalTextures:
    def __init__(self):
        self.x = game.tile_size * 8
        self.y = game.tile_size * 8
        self.w = 8
        self.h = 8
        self.id = None
        self.color = Colors.WHITE
        self.angle = radians(-90)
        self.arrow_img = Image(
            imgload(
                "client", "assets", "images", "minimap", "player_arrow.png", scale=1
            )
        )
        self.arrow_rect = pygame.Rect(0, 0, 16, 16)
        self.rect = pygame.FRect((self.x, self.y, self.w, self.h))
        self.wall_textures = [
            (
                Texture.from_surface(
                    display.renderer,
                    pygame.transform.scale_by(
                        pygame.image.load(
                            Path("client", "assets", "images", "3d", file_name + ".png")
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
                imgload("client", "assets", "images", "objects", file_name + ".png")
                if file_name is not None
                else None
            )
            for file_name in weapon_names
        ]

        self.highlighted_object_textures = [
            (
                Texture.from_surface(
                    display.renderer,
                    borderize(
                        pygame.image.load(
                            Path(
                                "client",
                                "assets",
                                "images",
                                "objects",
                                file_name + ".png",
                            )
                        ),
                        Colors.YELLOW,
                    ),
                )
                if file_name is not None
                else None
            )
            for file_name in weapon_names
        ]

        self.mask_object_textures = []
        for file_name_with_ext in weapon_names:
            if file_name_with_ext is None:
                tex = None
            else:
                surf = pygame.mask.from_surface(
                    pygame.image.load(
                        Path(
                            "client",
                            "assets",
                            "images",
                            "objects",
                            file_name_with_ext + ".png",
                        )
                    )
                ).to_surface(setcolor=Colors.WHITE)
                surf.set_colorkey(Colors.BLACK)
                tex = Texture.from_surface(display.renderer, surf)
            self.mask_object_textures.append(tex)
        self.weapon_textures = {
            weapon: [
                imgload(
                    "client",
                    "assets",
                    "images",
                    "weapons",
                    data["name"],
                    f"{data['name']}{i}.png",
                    scale=6,
                    return_rect=True,
                    colorkey=Colors.PINK,
                )
                for i in range(1, 6)
            ]
            for weapon, data in weapon_data.items()
        }


class HUD:
    def __init__(self):
        self.health_tex = None
        self.ammo_tex = None
        self.weapon_name_tex = None
        self.weapon_tex = None
        self.heart_tex = Texture.from_surface(
            display.renderer,
            pygame.image.load(Path("client", "assets", "images", "hud", "heart.png")),
        )
        self.heart_rect = self.heart_tex.get_rect(
            bottomright=(140, display.height - 12)
        )

    def update(self):
        if self.health_tex is not None:
            display.renderer.blit(self.health_tex, self.health_rect)
        if self.ammo_tex is not None:
            display.renderer.blit(self.ammo_tex, self.ammo_rect)
            w, h = 3, 25
            for yo in range(weapon_data[player.weapon]["mag"]):
                color = Colors.WHITE if yo < player.mag else Colors.GRAY
                yo = -yo * w * 4
                fill_rect(
                    color,
                    (
                        self.ammo_rect.x + yo - 15,
                        self.ammo_rect.centery - h / 2 + 2,
                        w,
                        h,
                    ),
                )

        if self.weapon_name_tex is not None:
            display.renderer.blit(self.weapon_name_tex, self.weapon_name_rect)
        if self.weapon_tex is not None:
            display.renderer.blit(self.weapon_tex, self.weapon_rect)

        display.renderer.blit(self.heart_tex, self.heart_rect)

    def update_weapon_general(self, player):
        self.update_weapon_tex(player)
        self.update_ammo(player)
        self.update_weapon_name(player)

    def update_health(self, player):
        self.health_tex, self.health_rect = write(
            "bottomleft",
            str(player.health),
            v_fonts[64],
            Colors.WHITE,
            16,
            display.height - 4,
        )

    def update_ammo(self, player):
        self.ammo_tex, self.ammo_rect = write(
            "bottomright",
            player.ammo,
            v_fonts[64],
            Colors.WHITE,
            display.width - 120,
            display.height - 4,
        )

    def update_weapon_name(self, player):
        self.weapon_name_tex, self.weapon_name_rect = write(
            "bottomright",
            weapon_names[int(player.weapon)].title(),
            v_fonts[32],
            Colors.WHITE,
            display.width - 16,
            self.ammo_rect.y,
        )

    def update_weapon_tex(self, player):
        self.weapon_tex = gtex.mask_object_textures[int(player.weapon)]
        self.weapon_rect = self.weapon_tex.get_rect()
        m = 3
        self.weapon_rect.inflate_ip(
            self.weapon_rect.width * m, self.weapon_rect.height * m
        )
        self.weapon_rect.center = (display.width - 60, display.height - 40)


class PlayerSelector:
    def __init__(self):
        self.database = {
            os.path.splitext(file)[0]: pygame.image.load(Path("client", "assets", "images", "player_skins", file)) for file in os.listdir(Path("client", "assets", "images", "player_skins"))
        }
        self.image = self.database["WHITE_RED"]
        # self.image = pygame.transform.scale_by(self.image, (4, 4))
        self.tex = Texture.from_surface(display.renderer, self.image)
        self.rect = self.image.get_rect(midright=(display.width - 120, display.height / 2))
        self.prim_color = 0
        self.sec_color = 0
        self.colors = {color: getattr(Colors, color) for color in vars(Colors) if not color.startswith("ANSI_") and not color.startswith("__")}
        del self.colors["GRAY"]
        self.color_keys = list(self.colors.keys())
        self.color_values = list(self.colors.values())
        self.prim_colorkey = Colors.WHITE
        self.sec_colorkey = Colors.RED
        self.colors_equal = False
        self.set_skin()
    
    def update(self):
        o = 10
        outline = pygame.Rect(self.rect.x - o, self.rect.y - o * 5, self.rect.width + o * 2, self.rect.height + o * 7)
        fill_rect(Colors.GRAY, outline)
        draw_rect(Colors.WHITE, outline)
        display.renderer.blit(self.tex, self.rect)
        draw_rect(Colors.RED, self.rect)
        write("midleft", self.color_keys[self.prim_color].replace("_", " "), v_fonts[50], Colors.WHITE, prim_skin_button.rect.right + 100, prim_skin_button.rect.centery)
        write("midleft", self.color_keys[self.sec_color].replace("_", " "), v_fonts[50], Colors.WHITE, sec_skin_button.rect.right + 100, sec_skin_button.rect.centery)
    
    def get_prim_skin(self):
        return self.prim_color

    def get_sec_skin(self):
        return self.sec_color

    def set_prim_skin(self, amount):
        self.prim_color += amount
        if self.prim_color == len(self.color_keys):
            self.prim_color = 0
        elif self.prim_color < 0:
            self.prim_color = len(self.color_keys) - 1
        self.set_skin()
    
    def set_sec_skin(self, amount):
        self.sec_color += amount
        if self.sec_color == len(self.color_keys):
            self.sec_color = 0
        elif self.sec_color < 0:
            self.sec_color = len(self.color_keys) - 1
        self.set_skin()
    
    def set_skin(self):
        prim = self.color_keys[self.prim_color]
        sec = self.color_keys[self.sec_color]
        name = f"{prim}_{sec}"
        self.colors_equal = prim == sec
        self.image = self.database[name]
        self.image = self.image.subsurface((0, 0, self.image.get_width() / 4, self.image.get_height()))
        self.rect = self.image.get_rect(topleft=self.rect.topleft)
        self.rect.topright = (display.width - 135, 200)
        self.tex = Texture.from_surface(display.renderer, self.image)

    """
    def set_prim_skin(self, amount):
        self.prim_color += amount
        if self.prim_color == len(self.color_values):
            self.prim_color = 0
        elif self.prim_color == -1:
            self.prim_color = len(self.color_values) - 1
        
        rgba = getattr(Colors, self.color_keys[self.prim_color])
        for y in range(self.image.get_height()):
            for x in range(self.image.get_width()):
                if self.image.get_at((x, y)) == self.prim_colorkey:
                    self.image.set_at((x, y), rgba)
        self.prim_colorkey = rgba
        self.tex = Texture.from_surface(display.renderer, self.image)
        
    def set_sec_skin(self, amount):
        self.sec_color += amount
        if self.sec_color == len(self.color_values):
            self.sec_color = 0
        elif self.sec_color == -1:
            self.sec_color = len(self.color_values) - 1

        rgba = getattr(Colors, self.color_keys[self.sec_color])
        for y in range(self.image.get_height()):
            for x in range(self.image.get_width()):
                if self.image.get_at((x, y)) == self.sec_colorkey:
                    self.image.set_at((x, y), rgba)
        self.sec_colorkey = rgba
        print(self.sec_colorkey)
        self.tex = Texture.from_surface(display.renderer, self.image)
    """
    
    def set_all_skins(self):
        self.image_copy = self.image.copy()
        i = 0
        imax = len(self.color_keys) ** 2
        for name, rgba in self.colors.items():
            for iname, irgba in self.colors.items():
                if name != iname or True:
                    for y in range(self.image.get_height()):
                        for x in range(self.image.get_width()):
                            if self.image_copy.get_at((x, y)) == Colors.WHITE:
                                self.image.set_at((x, y), rgba)
                            elif self.image_copy.get_at((x, y)) == Colors.RED:
                                self.image.set_at((x, y), irgba)
                    pygame.image.save(self.image, Path("client", "assets", "images", "player_skins", f"{name}_{iname}.png"))
                    i += 1
                    print(f"{i}/{imax}")


class Player:
    def __init__(self):
        self.x = game.tile_size * 8
        self.y = game.tile_size * 8
        self.w = 8
        self.h = 8
        self.tcp_id = client_tcp.getsockname()
        self.color = Colors.WHITE
        self.angle = radians(-90)
        self.arrow_img = Image(
            imgload(
                "client", "assets", "images", "minimap", "player_arrow.png", scale=1
            )
        )
        self.arrow_rect = pygame.Rect(0, 0, 16, 16)
        self.rect = pygame.FRect((self.x, self.y, self.w, self.h))
        # weapon and shooting tech
        self.weapons = []
        self.ammos = []
        self.mags = []
        self.weapon_index = 0
        self.weapon_anim = 1
        self.shooting = False
        self.reloading = False
        self.reload_direc = 1
        self.weapon_yoffset = 0
        self.health = 100
        hud.update_health(self)

        self.weapon_hud_tex = self.weapon_hud_rect = None
        self.last_shot = ticks()

        self.melee_anim = 1
        self.process_shot: bool | None = None
        self.last_melee = ticks()

        self.bob = 0
        self.to_equip: tuple[tuple[int, int], int] | None = None

    @property
    def weapon(self):
        try:
            return self.weapons[self.weapon_index]
        except IndexError:
            return None

    @property
    def mag(self):
        try:
            return self.mags[self.weapon_index]
        except IndexError:
            return None

    @mag.setter
    def mag(self, value):
        self.mags[self.weapon_index] = value

    @property
    def ammo(self):
        try:
            return self.ammos[self.weapon_index]
        except IndexError:
            return None

    @ammo.setter
    def ammo(self, value):
        self.ammos[self.weapon_index] = value

    def display_weapon(self):
        if self.weapon is not None:
            weapon_data = gtex.weapon_textures[self.weapon]
            if self.shooting:
                self.weapon_anim += 0.2
            try:
                weapon_data[int(self.weapon_anim)]
            except IndexError:
                self.shooting = False
                self.weapon_anim = 1
            weapon_tex = weapon_data[int(self.weapon_anim)][0]
            weapon_rect = weapon_data[int(self.weapon_anim)][1]
            weapon_rect.midbottom = (
                display.width / 2,
                display.height + self.weapon_yoffset,
            )
            if self.reloading:
                # reload down
                if weapon_rect.y >= display.height - 180:
                    self.reload_direc = -self.reload_direc
                # reload back up and get the ammo and magazine that was promised to you beforehand
                if self.weapon_yoffset == 0 and self.reload_direc == -1:
                    self.reloading = False
                    self.mag = self.new_mag
                    self.ammo = self.new_ammo
                    hud.update_weapon_general(self)
            display.renderer.blit(weapon_tex, weapon_rect)

    def draw(self):
        self.arrow_rect.center = self.rect.center
        self.arrow_img.angle = degrees(self.angle)
        display.renderer.blit(
            self.arrow_img,
            pygame.Rect(
                self.arrow_rect.x + game.mo,
                self.arrow_rect.y + game.mo,
                *self.arrow_rect.size,
            ),
        )
        # draw_rect(Colors.GREEN, self.rect)
        if self.to_equip is not None:
            coord, obj = self.to_equip
            weapon_id, weapon_orien = obj
            weapon_name = weapon_names[int(weapon_id)].title()
            # weapon_name =
            cost = weapon_costs[weapon_id]
            write(
                "midbottom",
                f"Press <e> to buy {weapon_name} [${cost}]",
                v_fonts[52],
                Colors.WHITE,
                display.width / 2,
                display.height - 50,
            )
            if joystick is not None:
                joystick_button_rect.midbottom = (
                    display.width / 2 - 115,
                    display.height - 42,
                )
                display.renderer.blit(
                    joystick_button_sprs[Joymap.SQUARE], joystick_button_rect
                )

    def render_map(self):
        game.mo = game.tile_size * 0
        game.map_rect = game.map_tex.get_rect(topleft=(game.mo, game.mo))
        game.rendered_enemies = 0
        self.walls_to_render.sort(key=lambda x: -x[0])
        for dist_px, tex, dest, area, color in self.walls_to_render:
            # # render enemy first
            if self.enemies_to_render:
                enemy = self.enemies_to_render[0]
                if enemy.dist_px > dist_px:
                    enemy.render()
                    del self.enemies_to_render[0]
            # render the texture after the (farther away) enemy
            tex.color = color
            display.renderer.blit(tex, dest, area)
        # render the remaining enemies
        for enemy in self.enemies_to_render:
            enemy.render()

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
            game.current_object_map[y][x] = "0"
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
            if keys[pygame.K_w]:
                xvel, yvel = angle_to_vel(self.angle, vmult)
            if keys[pygame.K_a]:
                xvel, yvel = angle_to_vel(self.angle - pi / 2, vmult)
            if keys[pygame.K_s]:
                xvel, yvel = angle_to_vel(self.angle + pi, vmult)
            if keys[pygame.K_d]:
                xvel, yvel = angle_to_vel(self.angle + pi / 2, vmult)
            
            if keys[pygame.K_q]:
                  for enemy in enemies:
                    enemy.indicator_rect.y -= 1

            if keys[pygame.K_q]:
                self.melee()

            amult = 0.03
            if keys[pygame.K_LEFT]:
                self.angle -= amult
            if keys[pygame.K_RIGHT]:
                self.angle += amult
            m = 12
            if keys[pygame.K_UP]:
                self.bob += m
            if keys[pygame.K_DOWN]:
                self.bob -= m

            # joystick isn't actually a literal joystick, pygame input term for gamepad
            if joystick is not None:
                # movement
                thr = 0.06
                ax0 = joystick.get_axis(Joymap.LEFT_JOYSTICK_HOR)
                ax1 = joystick.get_axis(Joymap.LEFT_JOYSTICK_VER)
                if abs(ax0) <= thr:
                    ax0 = 0
                if abs(ax1) <= thr:
                    ax1 = 0
                theta = pi2pi(player.angle) + 0.5 * pi
                ax0p = ax0 * cos(theta) - ax1 * sin(theta)
                ax1p = ax0 * sin(theta) + ax1 * cos(theta)
                thr = 0.06
                # run mechanics
                if joystick.get_button(Joymap.LEFT_JOYSTICK_CLICK):
                    run_m = 2
                    ax0p *= run_m
                    ax1p *= run_m
                if ax0p != 0 or ax1p != 0:
                    xvel, yvel = ax0p * vmult, ax1p * vmult
                # rotation
                hor_m = 0.0005 * game.sens
                ver_m = -0.4 * game.sens
                ax2 = joystick.get_axis(Joymap.RIGHT_JOYSTICK_HOR)
                ax3 = joystick.get_axis(Joymap.RIGHT_JOYSTICK_VER)
                if abs(ax2) <= thr:
                    ax2 = 0
                if abs(ax3) <= thr:
                    ax3 = 0
                rot_xvel = ax2 * hor_m
                self.bob += ax3 * ver_m
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
        self.start_x = (
            self.rect.centerx + cos(self.angle) * game.zoom
        ) / game.tile_size
        self.start_y = (
            self.rect.centery + sin(self.angle) * game.zoom
        ) / game.tile_size

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
            start_x, start_y = (
                self.rect.centerx / game.tile_size,
                self.rect.centery / game.tile_size,
            )
            self.cast_ray(0, 0, start_x, start_y)
        else:
            o = -game.fov // 2
            for index in range(game.ray_density + 1):
                self.cast_ray(o, index)
                o += game.fov / game.ray_density
        _xvel, _yvel = angle_to_vel(self.angle)

        for enemy in enemies:
            dy = enemy.indicator_rect.centery - self.rect.centery
            dx = enemy.indicator_rect.centerx - self.rect.centerx
            enemy.angle = degrees(atan2(dy, dx))
            enemy.dist_px = hypot(dy, dx)
        self.enemies_to_render = sorted(enemies, key=lambda te: te.dist_px, reverse=True)

        # map ofc
        self.render_map()

        # processing other important joystick input
        shoot_auto = False
        if joystick is not None:
            # picking up wall items
            if joystick.get_button(Joymap.SQUARE):
                self.try_to_buy_wall_weapon()
            # shoot with joystick
            ax = joystick.get_axis(Joymap.RIGHT_TRIGGER)
            shoot = ax > -1
        else:
            if self.weapon in weapon_data:
                if weapon_data[self.weapon]["auto"]:
                    mouses = pygame.mouse.get_pressed()
                    shoot_auto = mouses[0]
                else:
                    if self.weapon is not None:
                        if shoot_auto or self.process_shot:
                            if self.mag == 0:
                                self.reload()
                            elif not self.reloading:
                                self.shoot()

        # check whether reloading
        if self.reloading:
            m = 6
            self.weapon_yoffset += self.reload_direc * m

    def shoot(self):
        if ticks() - self.last_shot >= weapon_data[self.weapon]["fire_pause"]:
            self.shooting = True
            self.weapon_anim = 1
            channel.play(sound)

            for enemy in enemies:
                if enemy.rendering and not enemy.regenerating:
                    if enemy.rect.collidepoint(display.center):
                        # the body in general is hit
                        mult = 1
                        if enemy.head_rect.collidepoint(display.center):
                            mult = 1.4
                        elif enemy.legs_rect.collidepoint(display.center) or enemy.shoulder1_rect.collidepoint(display.center) or enemy.shoulder2_rect.collidepoint(display.center):
                            mult = 0.5
                        enemy.hit(mult)

            self.last_shot = ticks()
            self.mag -= 1
            hud.update_weapon_general(self)

    def reload(self, amount=None):
        if self.mag < weapon_data[self.weapon]["mag"]:
            if not self.reloading:
                self.reloading = True
                self.reload_direc = 1
                self.new_mag = weapon_data[self.weapon]["mag"]
                self.mag_diff = self.new_mag - self.mag
                self.new_ammo = self.ammo - self.mag_diff

    def cast_ray(
        self, deg_offset, index, start_x=None, start_y=None, abs_angle=False
    ):  # add comments here pls
        offset = radians(deg_offset)
        if not abs_angle:
            angle = self.angle + offset
        else:
            angle = offset
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
            tile_value = game.current_map[cur_y][cur_x]
            if tile_value != 0:
                col = True
        if col:
            # object (wall weapon)
            obj = game.current_object_map[cur_y][cur_x]
            # general ray calculations (big branin)
            p1 = (start_x * game.tile_size, start_y * game.tile_size)
            p2 = (
                p1[0] + dist * dx * game.tile_size,
                p1[1] + dist * dy * game.tile_size,
            )
            ray_mult = 1
            dist *= ray_mult
            dist_px = dist * game.tile_size
            self.rays.append(((p1, p2), dist_px))
            # init vars for walls
            ww = display.width / game.ray_density
            # wh = display.height * game.tile_size / dist_px * 1.7  # brute force
            wh = game.projection_dist / dist_px * display.height / 2  # maths
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

            # texture rendering
            if tile_value == -1:
                return

            tex = gtex.wall_textures[tile_value]
            axo = tex_d / game.tile_size * tex.width
            tex.color = [int(min(wh * 2 / display.height * 255, 255))] * 3
            self.walls_to_render.append(
                (
                    dist_px,
                    tex,
                    pygame.Rect(wx, wy, ww, wh),
                    pygame.Rect(axo, 0, 1, tex.height),
                    tex.color,
                )
            )
            # check whether the wall weapon is in the correct orientation
            if len(obj) > 1:
                if int(obj[1]) == orien:
                    high = (cur_x, cur_y) in self.surround
                    if high:
                        lookup = gtex.highlighted_object_textures
                        self.to_equip = ((cur_x, cur_y), obj)
                    else:
                        lookup = gtex.object_textures
                    tex = lookup[int(obj[0])]
                    tex.color = [int(min(wh * 2 / display.height * 255, 255))] * 3
                    self.walls_to_render.append(
                        (
                            dist_px,
                            tex,
                            pygame.Rect(wx, wy, ww, wh),
                            pygame.Rect(axo + high, 0, 1, tex.height),
                            tex.color,
                        )
                    )

    def send_location(self):
        client_udp.req(json.dumps({
            "tcp_id": str(self.tcp_id),
            "body": {
                "x": self.arrow_rect.x + game.mo,
                "y": self.arrow_rect.y + game.mo,
                "angle": self.angle,
            }
        }))

    def set_weapon(self, weapon):
        weapon = int(weapon)
        self.weapon_hud_tex = gtex.mask_object_textures[weapon]
        self.weapon_hud_rect = self.weapon_hud_tex.get_rect(
            bottomright=(display.width - 160, display.height - 10)
        ).scale_by(4)
        weapon = str(weapon)
        if len(self.weapons) == 2:
            self.weapons[self.weapon_index] = weapon
            self.ammos[self.weapon_index] = weapon_data[weapon]["ammo"]
            self.mags[self.weapon_index] = weapon_data[weapon]["mag"]
        elif len(self.weapons) == 1:
            self.weapons[1] = weapon
            self.ammos[1] = weapon_data[weapon]["ammo"]
            self.mags[1] = weapon_data[weapon]["mag"]
            self.weapon_index = 1
        else:
            self.weapons.append(weapon)
            self.ammos.append(weapon_data[weapon]["ammo"])
            self.mags.append(weapon_data[weapon]["mag"])
        hud.update_weapon_general(self)

    def update(self):
        if game.multiplayer:
            self.send_location()
            if client_tcp.current_message:
                if client_tcp.current_message.startswith("take_damage"):
                    self.health = max(
                        self.health - int(client_tcp.current_message.split("|")[1]), 0
                    )
                    hud.update_health(self)

                    if self.health <= 0:
                        client_tcp.req(f"kill|{self.tcp_id}")
                        game.set_state(States.MAIN_MENU)
                    
                    client_tcp.current_message = ""

                if client_tcp.current_message == f"kill|{self.tcp_id}":
                    client_tcp.current_message = ""
                    game.set_state(States.MAIN_MENU)
                    return
                
                if client_tcp.current_message.startswith("init_player"):
                    msg = client_tcp.current_message.split("|")
                    for enemy in enemies:
                        if enemy.id_ == msg[1]:
                            data = json.loads(msg[2])
                            enemy.health = data["health"]
                            enemy.image.color = data["color"]
                            enemy.name = data["name"]

                    client_tcp.current_message = ""

        self.rays = []
        self.walls_to_render = []
        self.enemies_to_render = []
        self.keys()

        # updates
        ...


        for data in self.rays:
            ray, _ = data
            p1 = (ray[0][0] + game.mo, ray[0][1] + game.mo)
            p2 = (ray[1][0] + game.mo, ray[1][1] + game.mo)
            draw_line(Colors.GREEN, p1, p2)
        player.display_weapon()



class EnemyPlayer:
    def __init__(self, id_=None):
        self.id_: str = id_
        self.x = int(game.tile_size * rand(0, game.map_width - 3))
        self.y = int(game.tile_size * rand(0, game.map_height - 3))
        self.w = 8
        self.h = 8
        self.angle = radians(-90)
        self.indicator = imgload(
            "client", "assets", "images", "minimap", "player_arrow.png"
        )
        self.indicator.color = Colors.ORANGE
        self.indicator_rect = pygame.Rect((0, 0, 16, 16))
        self.indicator_rect.center = (self.x, self.y)
        self.last_hit = ticks()
        self.regenerating = False
        self.rendering = False
        self.images = imgload(
            "client", "assets", "images", "3d", "player.png", frames=4
        )
        self.image = self.images[0]
        self.color = [rand(0, 255) for _ in range(3)] + [255]
        self.image.color = self.color
        self.health = 100  # currently not being updated
        self.name: str = None

    def draw(self):
        if game.multiplayer:
            if client_udp.current_message:
                message = json.loads(client_udp.current_message)
                if self.id_ not in message:
                    self.die()
                    return
                self.indicator_rect.x = message[self.id_]["x"]
                self.indicator_rect.y = message[self.id_]["y"]
                self.angle = message[self.id_]["angle"]

        self.rendering = False
        draw_rect(Colors.RED, self.indicator_rect)
        display.renderer.blit(self.indicator, self.indicator_rect)

    def update(self):
        if game.multiplayer:
            if self.health <= 0:
                print(f"requesting to kill {self.id_}")
                client_tcp.req(f"kill|{self.id_}")

            if client_tcp.current_message == f"kill|{self.id_}":
                client_tcp.current_message = ""
                self.die()
                return

        # print("enemy health:", self.health)
        self.draw()
        self.regenerate()

    def render(self):
        start_angle = degrees(pi2pi(player.angle)) - game.fov // 2
        angle = self.angle
        end_angle = start_angle + (game.ray_density + 1) * game.fov / game.ray_density

        if is_angle_between(start_angle, angle, end_angle):
            game.rendered_enemies += 1
            diff1 = angle_diff(start_angle, angle)
            diff2 = angle_diff(angle, end_angle)
            ratio = (diff1) / (diff1 + diff2)
            centerx = ratio * display.width
            centery = display.height / 2 + player.bob
            height = game.projection_dist / self.dist_px * display.height / 2  # maths
            width = height / self.image.height * self.image.width
            # rects
            og_width, og_height = 232, 400
            head_w_ratio = 84 / og_width
            head_h_ratio = 88 / og_height
            torso_w_ratio = 92 / og_width
            torso_h_ratio = 148 / og_height
            legs_w_ratio = 100 / og_width
            legs_h_ratio = 168 / og_height
            shoulder_w_ratio = 28 / og_width
            shoulder_h_ratio = 84 / og_height
            arm_w_ratio = 11 / og_width
            arm_h_ratio = 50 / og_height
            # whole body
            self.rect = pygame.Rect(0, 0, width, height)
            self.rect.center = (centerx, centery)
            # head
            self.head_rect = pygame.Rect(0, 0, head_w_ratio * width, head_h_ratio * height)
            self.head_rect.midtop = (self.rect.centerx, self.rect.top)
            # torso
            self.torso_rect = pygame.Rect(0, 0, torso_w_ratio * width, torso_h_ratio * height)
            self.torso_rect.midtop = (self.rect.centerx, self.head_rect.bottom)
            # legs
            self.legs_rect = pygame.Rect(0, 0, legs_w_ratio * width, legs_h_ratio * height)
            self.legs_rect.midtop = (self.rect.centerx, self.torso_rect.bottom)
            # shoulders
            self.shoulder1_rect = pygame.Rect(0, 0, shoulder_w_ratio * width, shoulder_h_ratio * height)
            self.shoulder1_rect.topright = self.torso_rect.topleft
            self.shoulder2_rect = pygame.Rect(0, 0, shoulder_w_ratio * width, shoulder_h_ratio * height)
            self.shoulder2_rect.topleft = self.torso_rect.topright
            # arms
            self.arm1_rect = pygame.Rect(0, 0, arm_w_ratio * width, arm_h_ratio * height)
            self.arm1_rect.topright = self.shoulder1_rect.topleft
            self.arm2_rect = pygame.Rect(0, 0, arm_w_ratio * width, arm_h_ratio * height)
            self.arm2_rect.topleft = self.shoulder2_rect.topleft
            # rest
            display.renderer.blit(self.image, self.rect)
            draw_rect(Colors.YELLOW, self.rect)
            draw_rect(Colors.ORANGE, self.head_rect)
            draw_rect(Colors.LIGHT_BLUE, self.torso_rect)
            draw_rect(Colors.GREEN, self.shoulder1_rect)
            draw_rect(Colors.GREEN, self.shoulder2_rect)
            draw_rect(Colors.BLUE, self.arm1_rect)
            draw_rect(Colors.BLUE, self.arm2_rect)
            self.rendering = True

    def regenerate(self):
        if self.regenerating and ticks() - self.last_hit >= 70:
            self.regenerating = False
            self.image.color = self.color

    def hit(self, mult):
        self.image.color = Colors.RED
        self.last_hit = ticks()
        self.regenerating = True
        damage = int(weapon_data[player.weapon]["damage"] * mult)
        client_tcp.req(f"damage|{self.id_}|{damage}")
        if self.health <= 0:
            self.update() # for dying

    def die(self):
        try:
            enemies.remove(self)
            enemy_addresses.remove(self.id_)
        except:
            pass

cursor.enable()
game = Game()
hud = HUD()
player_selector = PlayerSelector()
# player_selector.set_all_skins()
gtex = GlobalTextures()
player: Player = None # initialization is in game.set_state
enemies: list[EnemyPlayer] = []
enemy_addresses: list[str] = []
clock = pygame.time.Clock()
joystick: pygame.joystick.JoystickType = None

crosshair_tex = imgload("client", "assets", "images", "hud", "crosshair.png", scale=3)
crosshair_rect = crosshair_tex.get_rect(center=(display.center))

title = Button(
    int(display.width / 2),
    150,
    "PANDEMONIUM",
    None,
    font_size=96,
    anchor="center",
)

username_input = UserInput(
    player_selector.rect.centerx,
    player_selector.rect.y - 40,
    40,
    Colors.WHITE        
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
            grayed_out_when=lambda: player_selector.colors_equal
        ),
        Button(
            80,
            display.height / 2 + 48 * 1,
            "Settings",
            lambda: game.set_state(States.MAIN_SETTINGS),
        ),
        Button(
            80,
            display.height / 2 + 48 * 2,
            "Exit",
            game.stop_running,
        ),
        Button(
            player_selector.rect.centerx - 98,
            player_selector.rect.bottom + 20,
            "Skin",
            player_selector.set_prim_skin,
            action_arg=1,
            is_slider=True,
            slider_display=player_selector.get_prim_skin,
            font_size=50,
            anchor="midtop",
        ),
        Button(
            player_selector.rect.centerx - 98,
            player_selector.rect.bottom + 60,
            "Skin",
            player_selector.set_sec_skin,
            action_arg=1,
            is_slider=True,
            slider_display=player_selector.get_sec_skin,
            font_size=50,
            anchor="midtop",
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
    States.PLAY: [],
}
prim_skin_button = all_buttons[States.MAIN_MENU][4]
sec_skin_button = all_buttons[States.MAIN_MENU][5]


class Hue:
    def __init__(self, color, alpha):
        self.surf = pygame.Surface((display.width, display.height), pygame.SRCALPHA)
        self.surf.fill(color)
        self.surf.set_alpha(alpha)
        self.tex = Texture.from_surface(display.renderer, self.surf)
        self.rect = self.surf.get_rect()


darken_game = Hue(Colors.BLACK, 80)
redden_game = Hue(Colors.RED, 20)

menu_wall_texs = imgload(
    "client", "assets", "images", "menu", "wallpaper", "wall.jpg", scale=1, frames=8
)
menu_wall_index = 0

floor_tex = imgload("client", "assets", "images", "3d", "floor.png")
joystick_button_sprs = imgload(
    "client", "assets", "images", "hud", "buttons.png", scale=4, frames=4
)
joystick_button_rect = joystick_button_sprs[0].get_rect()


def check_new_players():
    if client_udp.current_message:
        message = json.loads(client_udp.current_message)
        for addr in message:
            if addr not in enemy_addresses:
                enemy_addresses.append(addr)
                enemies.append(EnemyPlayer(addr))


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

    game.multiplayer = multiplayer
    if game.multiplayer:
        client_udp = Client("udp")
        client_tcp = Client("tcp")
        Thread(target=client_udp.receive, daemon=True).start()
        Thread(target=client_tcp.receive, daemon=True).start()

    game.set_state(States.MAIN_MENU)
    while game.running:
        clock.tick(game.fps)
        player.process_shot = False

        for event in pygame.event.get():
            match event.type:
                case pygame.QUIT:
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
                                player.bob -= event.rel[1] * game.sens / 100
                                player.bob = min(player.bob, display.height * 1.5)
                                player.bob = max(player.bob, -display.height * 1.5)

                case pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        if game.state == States.PLAY:
                            player.process_shot = True
                            # if event.button == 1:
                            #     game.target_zoom = 30
                            #     game.zoom = 0

                case pygame.MOUSEBUTTONUP:
                    if game.state == States.PLAY:
                        if event.button == 1:
                            game.target_zoom = 0

                case pygame.KEYDOWN:
                    if game.state == States.MAIN_MENU:
                        username_input.process_event(event)

                    match event.key:
                        case pygame.K_ESCAPE:
                            match game.state:
                                case States.PLAY_SETTINGS:
                                    game.set_state(States.PLAY)
                                case States.PLAY:
                                    game.set_state(States.PLAY_SETTINGS)

                        case pygame.K_e:
                            player.try_to_buy_wall_weapon()

                        case pygame.K_r:
                            if game.state == States.PLAY:
                                player.reload()

                        case pygame.K_SPACE:
                            enemies.append(EnemyPlayer())

                        case pygame.K_q:
                            for _ in range(3):
                                try:
                                    del enemies[rand(0, len(enemies) - 1)]
                                except:
                                    pass

                case pygame.JOYDEVICEADDED:
                    joystick = pygame.joystick.Joystick(event.device_index)

                case pygame.JOYBUTTONDOWN:
                    if event.button == Joymap.CROSS:
                        # player.jump() implement
                        ...

            for button in current_buttons:
                button.process_event(event)

        display.renderer.clear()

        if game.state == States.MAIN_MENU:
            # fill_rect(Colors.BLACK, (0, 0, display.width, display.height))
            display.renderer.blit(menu_wall_texs[0])
            player_selector.update()
            username_input.update()
        else:
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
                    if game.multiplayer:
                        check_new_players()
                        for enemy in enemies:
                            enemy.update()

                hud.update()

            display.renderer.blit(crosshair_tex, crosshair_rect)
            display.renderer.blit(redden_game.tex, redden_game.rect)

            if game.state == States.PLAY:
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

    sys.exit()
