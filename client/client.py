import pygame
import sys
import json
import os

from math import sin, cos, tan, atan2, pi, radians, degrees, sqrt, hypot
from pathlib import Path
from pygame._sdl2.video import Texture, Image
from threading import Thread
from random import randint as rand
from random import uniform as randf
from typing import Dict

from .include import *
import atexit


def quit():
    json_save = {
        "resolution": game.resolution,
        "fov": game.fov,
        "sens": game.sens,
        "volume": game.get_volume(),
        "max_fps_index": game.max_fps_index,
    }
    with open(Path("client", "settings.json"), "w") as f:
        json.dump(json_save, f)

    if game.multiplayer and client_tcp:
        client_tcp.req(f"quit|{player.tcp_id}|f4")

    game.running = False
    pygame.quit()
    print("Exited successfully")


atexit.register(quit)


class Game:
    def __init__(self):
        # settings values
        failed = False
        try:
            if os.path.isfile(Path("client", "settings.json")):
                with open(Path("client", "settings.json"), "r") as f:
                    json_load = json.load(f)
                    self.sens = json_load["sens"]
                    self.fov = json_load["fov"]
                    self.resolution = json_load["resolution"]
                    self.max_fps_index = json_load["max_fps_index"]
                    self.volume = json_load["volume"]
                    pygame.mixer.music.set_volume(self.volume)
            else:
                open(Path("client", "settings.json"), "w").close()
                failed = True
        except Exception:
            failed = True
        if failed:
            self.sens = 50
            self.fov = 60
            self.resolution = 2
            self.max_fps_index = 1
            self.volume = 1

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
        self.dt = 1

        self.target_zoom = self.zoom = 0
        self.zoom_speed = 0.4
        self.last_zoom = ticks()
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
        self.fps_list = (30, 60, 120, 144, 240, 1000)

    @property
    def rect_list(self):
        return sum(self.rects, [])

    def stop_running(self):
        self.running = False

    def set_state(self, target_state):
        global player, hud, leaderboard
        if target_state == States.MAIN_MENU:
            player = Player()
            hud = HUD()
            leaderboard = Leaderboard()
            hud.update_health(player)
            hud.update_score(player)
            hud.update_weapon_general(player)
        if (
            target_state == States.MAIN_MENU and self.state != States.MAIN_SETTINGS
        ) or (target_state == States.MAIN_SETTINGS and self.state != States.MAIN_MENU):
            pygame.mixer.music.load(Sounds.MAIN_MENU)
            pygame.mixer.music.play(-1)
        elif (target_state == States.PLAY and self.state != States.PLAY_SETTINGS) or (
            target_state == States.PLAY_SETTINGS and self.state != States.PLAY
        ):
            pygame.mixer.music.load(Sounds.PLAY)
            pygame.mixer.music.play(-1)

        if (
            game.multiplayer
            and target_state == States.PLAY
            and self.state == States.MAIN_MENU
        ):
            # All launch & init requirements
            leaderboard.texs[player.tcp_id] = (text2tex(username_input.text, 32), None)
            msg = json.dumps(
                {
                    "health": player.health,
                    "prim_color": player_selector.get_prim_skin(),
                    "sec_color": player_selector.get_sec_skin(),
                    "name": username_input.text,
                }
            )
            client_tcp.req(f"init_player|{player.tcp_id}|{msg}")

        self.previous_state = self.state
        self.state = target_state

        if self.state == States.PLAY:
            cursor.disable()
        else:
            cursor.enable()

        global current_buttons
        current_buttons = all_buttons[self.state]

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

    def set_volume(self, amount):
        # 0.05 is for rounding to steps of 5
        self.volume = 0.05 * round(
            (pygame.mixer.music.get_volume() + amount / 100) / 0.05
        )

        pygame.mixer.music.set_volume(self.volume)
        [channel.set_volume(self.volume) for channel in player.audio_channels]
        for enemy in enemies.copy():
            [channel.set_volume(self.volume) for channel in enemy.audio_channels]

    def get_volume(self):
        # 0.05 is for floating point inaccuracy
        return int(5 * round(pygame.mixer.music.get_volume() / 0.05))

    def set_max_fps(self, arg):
        self.max_fps_index += arg
        self.max_fps_index = max(0, min(self.max_fps_index, len(self.fps_list) - 1))

    def get_max_fps(self):
        return self.fps_list[self.max_fps_index]


class GlobalTextures:
    def __init__(self):
        self.x = game.tile_size * 8
        self.y = game.tile_size * 8
        self.w = 1
        self.h = 1
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
            for file_name in [None, "wall", "floor"]
        ]
        self.object_textures = [
            (
                imgload("client", "assets", "images", "objects", file_name + ".png")
                if file_name is not None and file_name not in ("Knife", "Pistol")
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
                if file_name is not None and file_name not in ("Knife", "Pistol")
                else None
            )
            for file_name in weapon_names
        ]

        self.mask_object_textures = [
            (
                imgload("client", "assets", "images", "mask_objects", file_name + ".png")
                if file_name is not None and file_name not in ("Knife",)
                else None
            )
            for file_name in weapon_names
        ]
        self.weapon_textures = {
            weapon: [
                imgload(
                    "client",
                    "assets",
                    "images",
                    "weapons",
                    data["name"],
                    f"{data['name']}_{i}.png",
                    scale=6,
                    return_rect=True,
                    colorkey=Colors.PINK,
                )
                for i in range(1, len(os.listdir(Path('client', 'assets', 'images', 'weapons', data['name']))) + 1)
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
            bottomright=(150, display.height - 12)
        )

    def update(self):
        if self.health_tex is not None:
            display.renderer.blit(self.health_tex, self.health_rect)
        if self.score_tex is not None:
            display.renderer.blit(self.score_tex, self.score_rect)
        if self.ammo_tex is not None:
            display.renderer.blit(self.ammo_tex, self.ammo_rect)
            w, h = 3, 25
            mag_size = weapon_data[player.weapon]["mag"]
            if mag_size <= 16:
                max_width = 80
                gap_width = (max_width - w * mag_size) / (mag_size - 1)
                mult = (gap_width + w)
                for xo in range(mag_size):
                    color = Colors.WHITE if xo < player.mag else Colors.GRAY
                    fill_rect(
                        color,
                        (
                            self.ammo_rect.x - xo * mult - 15,
                            self.ammo_rect.centery - h / 2 + 2,
                            w,
                            h,
                        ),
                    )
            else:
                display.renderer.blit(self.mag_tex, self.mag_rect)

        if self.weapon_name_tex is not None:
            display.renderer.blit(self.weapon_name_tex, self.weapon_name_rect)
        if self.weapon_tex is not None:
            display.renderer.blit(self.weapon_tex, self.weapon_rect)

        display.renderer.blit(self.heart_tex, self.heart_rect)
        for i, message in enumerate(feed):
            if ticks() - 5000 > message[1]:
                feed.remove(message)
            else:
                tex = message[0]
                display.renderer.blit(
                    tex,
                    tex.get_rect(topright=(display.width - 16, 16 + 32 * i)),
                )

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
    
    def update_score(self, player):
        self.score_tex, self.score_rect = write(
            "bottomleft",
            f"${player.score}",
            v_fonts[48],
            Colors.WHITE,
            16,
            self.health_rect.top
        )
        self.score_tex, self.score_rect = write(
            "bottomleft",
            f"${player.score}",
            v_fonts[48],
            Colors.WHITE,
            16,
            self.health_rect.top
        )

    def update_ammo(self, player):
        max_mag_size = weapon_data[player.weapon]["mag"]
        self.ammo_tex, self.ammo_rect = write(
            "midright",
            player.ammo,
            v_fonts[64],
            Colors.WHITE if player.ammo > 0 else Colors.RED,
            self.weapon_rect.left - 16,
            self.weapon_rect.centery,
        )
        if max_mag_size > 16:
            self.mag_tex, self.mag_rect = write(
                "bottomright",
                player.mag,
                v_fonts[46],
                Colors.WHITE,
                self.ammo_rect.left - 5,
                self.ammo_rect.bottom
            )

    def update_weapon_name(self, player):
        self.weapon_name_tex, self.weapon_name_rect = write(
            "bottomright",
            weapon_names[int(player.weapon)],
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
        self.weapon_rect.bottomright = (display.width - 10, display.height - 10)


class Leaderboard:
    def __init__(self):
        self.texs: Dict[str, tuple[Texture, Optional[int]]] = {}

    def update(self):
        # Sort by K/D
        scores: Dict[str, float] = {
            player.tcp_id: player.kills / player.deaths
            if player.deaths > 0 else player.kills
        } | {
                enemy.id: enemy.kills / enemy.deaths
                if enemy.deaths > 0 else enemy.kills
                for enemy in enemies
            }
        scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        new_texs: Dict[str, tuple[Texture, int]] = {}
        for (score_id, score) in scores:
            for texs_id, (tex, _) in self.texs.items():
                if texs_id == score_id:
                    new_texs[texs_id] = (tex, score)
                    break

        self.texs = new_texs

        print("self.texs", self.texs)

        # Render header
        for id, tex in {
            1: "Name",
            2: "Score",
            3: "Kills",
            4: "Deaths",
        }.items():
            tex = text2tex(tex, 32)
            display.renderer.blit(
                tex,
                tex.get_rect(
                    topleft=(display.width * id / 5, display.height / 8 - 32)
                )
            )

        # Render data
        for i, (id, (tex, _)) in enumerate(self.texs.items()):
            # Name
            display.renderer.blit(
                tex,
                tex.get_rect(
                    topleft=(display.width * 1 / 5, (display.height / 8) + (32 * i))
                ),
            )

            # Score
            dict1 = {player.tcp_id: player.score} | {enemy.id: enemy.score for enemy in enemies.copy()}
            array = [score for id_, score in dict1.items() if id_ == id]
            score_tex = text2tex(array[0], 32)
            display.renderer.blit(
                score_tex,
                score_tex.get_rect(
                    topleft=(display.width * 2 / 5, (display.height / 8) + (32 * i))
                )
            )

            # Kills
            dict1 = {player.tcp_id: player.kills} | {enemy.id: enemy.kills for enemy in enemies.copy()}
            array = [kills for id_, kills in dict1.items() if id_ == id]
            kills_tex = text2tex(array[0], 32)
            display.renderer.blit(
                kills_tex,
                kills_tex.get_rect(
                    topleft=(display.width * 3 / 5, (display.height / 8) + (32 * i))
                )
            )

            # Deaths
            dict1 = {player.tcp_id: player.deaths} | {enemy.id: enemy.deaths for enemy in enemies.copy()}
            array = [deaths for id_, deaths in dict1.items() if id_ == id]
            deaths_tex = text2tex(array[0], 32)
            display.renderer.blit(
                deaths_tex,
                deaths_tex.get_rect(
                    topleft=(display.width * 4 / 5, (display.height / 8) + (32 * i))
                )
            )




class PlayerSelector:
    def __init__(self):
        self.database = {
            os.path.splitext(file)[0]: pygame.image.load(
                Path("client", "assets", "images", "player_skins", file)
            )
            for file in os.listdir(Path("client", "assets", "images", "player_skins"))
        }
        self.image = self.database["WHITE_RED"]
        # self.image = pygame.transform.scale_by(self.image, (4, 4))
        self.tex = Texture.from_surface(display.renderer, self.image)
        self.rect = self.image.get_rect(
            midright=(display.width - 120, display.height / 2)
        )
        self.prim_color = 1
        self.sec_color = 0
        self.colors = {
            color: getattr(Colors, color)
            for color in vars(Colors)
            if not color.startswith("ANSI_") and not color.startswith("__")
        }
        del self.colors["GRAY"]
        self.color_keys = list(self.colors.keys())
        self.color_values = list(self.colors.values())
        self.prim_colorkey = Colors.WHITE
        self.sec_colorkey = Colors.RED
        self.colors_equal = False
        self.set_skin()
        # surf
        o = 10
        self.outline = pygame.Rect(
            self.rect.x - o,
            self.rect.y - o * 5,
            self.rect.width + o * 2,
            self.rect.height + o * 7,
        )
        #
        self.black_surf = pygame.Surface(self.outline.size, pygame.SRCALPHA)
        self.black_surf.fill((0, 0, 0, 120))
        self.black_tex = Texture.from_surface(display.renderer, self.black_surf)

    def init(self):
        unleash_button = all_buttons[States.MAIN_MENU][1]
        self.menu_bg_surf = pygame.Surface(
            (unleash_button.rect.width + 40, 220), pygame.SRCALPHA
        )
        self.menu_bg_surf.fill((0, 0, 0, 120))
        self.menu_bg_tex = Texture.from_surface(display.renderer, self.menu_bg_surf)
        self.menu_bg_rect = self.menu_bg_surf.get_rect(
            topleft=(unleash_button.rect.x - 20, unleash_button.rect.y - 20)
        )

    def update(self):
        display.renderer.blit(self.black_tex, self.outline)
        display.renderer.blit(self.menu_bg_tex, self.menu_bg_rect)
        display.renderer.blit(self.tex, self.rect)

        prim_skin_button = all_buttons[States.MAIN_MENU][5]
        sec_skin_button = all_buttons[States.MAIN_MENU][6]

        write(
            "midleft",
            self.color_keys[self.prim_color].replace("_", " "),
            v_fonts[50],
            Colors.WHITE,
            prim_skin_button.rect.right + 100,
            prim_skin_button.rect.centery,
        )
        write(
            "midleft",
            self.color_keys[self.sec_color].replace("_", " "),
            v_fonts[50],
            Colors.WHITE,
            sec_skin_button.rect.right + 100,
            sec_skin_button.rect.centery,
        )

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
        self.prim = prim = self.color_keys[self.prim_color]
        self.sec = sec = self.color_keys[self.sec_color]
        name = f"{prim}_{sec}"
        self.colors_equal = prim == sec
        self.image = self.database[name]
        self.image = self.image.subsurface(
            (0, 0, self.image.get_width() / 4, self.image.get_height())
        )
        self.rect = self.image.get_rect(topleft=self.rect.topleft)
        self.rect.topright = (display.width - 135, 200)
        self.tex = Texture.from_surface(display.renderer, self.image)

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
                    pygame.image.save(
                        self.image,
                        Path(
                            "client",
                            "assets",
                            "images",
                            "player_skins",
                            f"{name}_{iname}.png",
                        ),
                    )
                    i += 1


class Player:
    def __init__(self):
        self.x = game.tile_size * 8
        self.y = game.tile_size * 8
        self.w = 8
        self.h = 8
        self.score = 500
        self.kills = 0
        self.deaths = 0
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
        self.weapons = ["4", None]
        self.weapon_index = 0
        self.ammos = [weapon_data["4"]["ammo"], None]
        self.mags = [weapon_data["4"]["mag"], None]
        self.weapon_anim = 0
        # dynamic offsets and stuff
        self.shooting = False
        self.reloading = False
        self.switching_weapons = False
        self.reload_direc = 1
        self.weapon_switch_direc = 1
        self.weapon_reload_offset = 0
        self.weapon_switch_offset = 0
        self.weapon_ads_offset = 0
        self.weapon_ads_offset_target = None
        self.weapon_recoil_offset = 0
        self.weapon_recoil_func = lambda x: -e ** (-x + pi) * sin(x + pi)
        self.last_recoil = None
        # rest
        self.health = 100
        self.meleing = False
        self.moving = False

        self.weapon_hud_tex = self.weapon_hud_rect = None
        self.last_shot = ticks()

        self.melee_anim = 1
        self.process_shot: bool | None = None
        self.process_melee: bool | None = None
        self.last_melee = ticks()
        self.last_step = ticks()

        self.bob = 0
        self.to_equip: tuple[tuple[int, int], int] | None = None
        self.audio_channels = [pygame.mixer.find_channel() for _ in range(2)]

        if game.multiplayer:
            self.tcp_id = str(client_tcp.getsockname())
        
        # sound
        for channel in self.audio_channels:
            channel.set_volume(game.volume)
    
    @property
    def view_yoffset(self):
        return self.bob + self.weapon_recoil_offset
    
    @property
    def can_shoot(self):
        return not self.reloading and not self.switching_weapons

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
        if self.weapon is not None or self.meleing:
            weapon_data = gtex.weapon_textures["2" if self.meleing else self.weapon]
            if self.shooting:
                self.weapon_anim += 0.2 * game.dt
            try:
                weapon_data[int(self.weapon_anim)]
            except IndexError:
                self.shooting = False
                self.weapon_anim = 0
                if self.meleing:
                    self.meleing = False
            
            weapon_tex = weapon_data[int(self.weapon_anim)][0]
            self.weapon_rect = weapon_data[int(self.weapon_anim)][1]
            if self.weapon_ads_offset_target is not None:
                self.weapon_ads_offset += (
                    self.weapon_ads_offset_target - self.weapon_ads_offset
                ) * game.zoom_speed
                # elapsed = ticks() - game.last_zoom
                # if self.weapon_ads_offset_target == 0:
                #     if elapsed >= 500:
                #         self.weapon_ads_offset_target = None
                #         self.weapon_ads_offset = 0

        

            if self.reloading:
                # reload down
                if (
                    self.reload_direc == 1
                    and self.weapon_rect.y >= display.height - 180
                ):
                    self.reload_direc = -self.reload_direc
                # reload back up and get the ammo and magazine that was promised to you beforehand
                if self.reload_direc == -1 and self.weapon_reload_offset <= 0:
                    self.reloading = False
                    self.mag = self.new_mag
                    self.ammo = self.new_ammo
                    self.weapon_reload_offset = 0
                    hud.update_weapon_general(self)
            
            if self.switching_weapons:
                # switch down
                if (
                    self.weapon_switch_direc == 1
                    and self.weapon_rect.y >= display.height - 180
                ):
                    self.weapon_switch_direc = -self.weapon_switch_direc
                    self.weapon_index = int(not self.weapon_index)  # 0 -> 1, 1 -> 0
                    hud.update_weapon_general(self)
                # reload back up and get the ammo and magazine that was promised to you beforehand
                if self.weapon_switch_direc == -1 and self.weapon_switch_offset <= 0:
                    self.switching_weapons = False
                    self.weapon_switch_offset = 0
            
            self.weapon_rect.midbottom = (
                display.width / 2,
                display.height + self.weapon_reload_offset + self.weapon_switch_offset + self.weapon_ads_offset,
            )

            display.renderer.blit(weapon_tex, self.weapon_rect)

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
            weapon_name = weapon_names[int(weapon_id)]
            # weapon_name =
            cost = weapon_data[weapon_id]["cost"]
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
            # actually buy the wall weapon
            (x, y), obj = self.to_equip
            x, y = int(x), int(y)
            weapon = obj[0]
            self.set_weapon(weapon)
        else:
            # switch weapons
            self.switching_weapons = True
            self.weapon_switch_direc = 1

    def keys(self):
        # keyboard
        self.to_equip = None
        self.surround = []
        if game.state == States.PLAY:
            # doing the ADS
            mouses = pygame.mouse.get_pressed()
            if mouses[2]:  # right mouse button
                if not self.adsing and self.can_shoot:
                    if self.weapon is not None:
                        game.target_zoom = 15
                        game.zoom = 0
                        self.weapon_ads_offset_target = 32 * 6
                    self.adsing = True
            else:
                game.target_zoom = 0
                game.last_zoom = ticks()
                self.weapon_ads_offset_target = 0
                self.adsing = False
            # keyboard
            self.moving = False
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
            if keys[pygame.K_LSHIFT] or game.target_zoom > 0:
                xvel /= 2
                yvel /= 2
            xvel *= game.dt
            yvel *= game.dt
            if xvel or yvel:
                self.moving = True
                if ticks() - self.last_step >= 400:
                    # play sound perhaps?
                    self.last_step = ticks()
            else:
                self.last_step = ticks()

            amult = 0.03
            if keys[pygame.K_LEFT]:
                self.angle -= amult * game.dt
            if keys[pygame.K_RIGHT]:
                self.angle += amult * game.dt
            m = 12
            if keys[pygame.K_UP]:
                self.bob += m * game.dt
            if keys[pygame.K_DOWN]:
                self.bob -= m * game.dt

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
        if game.target_zoom > 0 and False:  # dit is voor debugging dus doet niks
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
        self.start_x_px = self.start_x * game.tile_size
        self.start_y_px = self.start_y * game.tile_size
        for enemy in enemies:
            dy = enemy.indicator_rect.centery - self.start_y_px
            dx = enemy.indicator_rect.centerx - self.start_x_px
            enemy.angle = degrees(atan2(dy, dx))
            enemy.dist_px = hypot(dy, dx)
        self.enemies_to_render = sorted(
            enemies, key=lambda te: te.dist_px, reverse=True
        )

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
                if self.weapon is not None:
                    if shoot_auto or self.process_shot:
                        if self.mag == 0:
                            self.reload()
                        elif self.can_shoot:
                            self.shoot()

        # melee?
        if self.process_melee:
            self.melee()
        
        # recoil
        if self.last_recoil is not None:
            elapsed = ticks() - self.last_recoil
            recoil_mult = weapon_data[self.weapon]["recoil_mult"]
            recoil_time = weapon_data[self.weapon]["recoil_time"]
            x = elapsed / recoil_time * 2 * pi
            self.weapon_recoil_offset = self.weapon_recoil_func(x) * recoil_mult
            if x >= 3 * pi:
                self.last_recoil = None

        # check whether reloading or switching weapons
        if self.reloading:
            m = 6
            self.weapon_reload_offset += self.reload_direc * m * game.dt
        if self.switching_weapons:
            m = 12
            self.weapon_switch_offset += self.weapon_switch_direc * m * game.dt

    def shoot(self, melee=False):
        if ticks() - self.last_shot >= weapon_data[self.weapon]["fire_pause"]:
            self.shooting = True
            self.weapon_anim = 1
            self.last_recoil = ticks()
            self.audio_channels[0].set_volume(game.volume)  # Might not be necessary, just in case
            # self.audio_channels[0].play(weapon_data[self.weapon]["shot_sound"])
            bullet_pos = list(display.center)
            radius = randf(0, crosshair.radius)
            angle = randf(0, 2 * pi)
            bullet_pos[0] += cos(angle) * radius
            bullet_pos[1] += sin(angle) * radius
            shots.append(Shot(bullet_pos))
            for enemy in enemies:
                if enemy.rendering and not enemy.regenerating:
                    if enemy.rect.collidepoint(bullet_pos):
                        # the body in general is hit
                        mult = 0
                        if not melee:
                            if enemy.head_rect.collidepoint(bullet_pos):
                                mult = 1.4
                            elif (
                                enemy.legs_rect.collidepoint(bullet_pos)
                                or enemy.shoulder1_rect.collidepoint(bullet_pos)
                                or enemy.shoulder2_rect.collidepoint(bullet_pos)
                                or enemy.arm1_rect.collidepoint(bullet_pos)
                                or enemy.arm2_rect.collidepoint(bullet_pos)
                            ):
                                mult = 0.5
                            elif enemy.torso_rect.collidepoint(bullet_pos):
                                mult = 1
                        if mult > 0:
                            enemy.hit(mult)

            self.last_shot = ticks()
            self.mag -= 1
            hud.update_weapon_general(self)
            if game.multiplayer:
                client_tcp.req(
                    f"shoot|{self.tcp_id}|{self.weapon}|{self.arrow_rect.x}|{self.arrow_rect.y}"
                )

    def reload(self, amount=None):
        if self.weapon is not None:
            if self.ammo > 0:
                if self.mag < weapon_data[self.weapon]["mag"]:
                    if not self.reloading:
                        game.target_zoom = 0
                        self.weapon_ads_offset_target = 0
                        self.adsing = False
                        self.reloading = True
                        self.reload_direc = 1
                        needed_mag = weapon_data[self.weapon]["mag"] - self.mag
                        supplied_mag = min(self.ammo, weapon_data[self.weapon]["mag"])
                        final_mag = min(needed_mag, supplied_mag)
                        self.new_ammo = self.ammo - final_mag
                        self.new_mag = self.mag + final_mag

    def melee(self):
        if not self.meleing:
            if ticks() - self.last_melee >= weapon_data["2"]["fire_pause"]:
                self.weapon_anim = 1
                for enemy in enemies:
                    dist = hypot(
                        enemy.indicator_rect.centerx - self.arrow_rect.centerx,
                        enemy.indicator_rect.centery - self.arrow_rect.centery,
                    )
                    if dist <= 20:
                        if enemy.rendering and not enemy.regenerating:
                            if enemy.rect.collidepoint(display.center):
                                # the body in general is hit
                                mult = 1
                                if (
                                    enemy.head_rect.collidepoint(display.center)
                                    or enemy.legs_rect.collidepoint(display.center)
                                    or enemy.shoulder1_rect.collidepoint(display.center)
                                    or enemy.shoulder2_rect.collidepoint(display.center)
                                    or enemy.arm1_rect.collidepoint(display.center)
                                    or enemy.arm2_rect.collidepoint(display.center)
                                ):
                                    mult = 1
                                if mult > 0:
                                    enemy.hit(mult, melee=True)

                self.meleing = True
                self.shooting = True
                self.weapon_anim = 0
                self.last_melee = ticks()

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
            dist_px = dist * game.tile_size * cos(offset)
            self.rays.append(((p1, p2), dist_px))
            # init vars for walls
            ww = display.width / game.ray_density
            # wh = display.height * game.tile_size / dist_px * 1.7  # brute force
            wh = (game.projection_dist / dist_px * display.height / 2) * (60 / game.fov)  # maths
            wx = index * ww
            wy = display.height / 2 - wh / 2 + self.view_yoffset
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

            tex = gtex.wall_textures[tile_value]
            axo = tex_d / game.tile_size * tex.width
            tex.color = [int(min(wh * 2 / display.height * 255, 255))] * 3
            # LSD SIMULATOR DONT DELETE
            # tex.color = [
            #     ((sin(ticks() * 0.01) + 1) / 2 * 255),
            #     ((sin(ticks() * 0.01 + (1 / 3) * 2 * pi) + 1) / 2 * 255),
            #     ((sin(ticks() * 0.01 + (2 / 3) * 2 * pi) + 1) / 2 * 255),
            # ]
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
        client_udp.req(
            json.dumps(
                {
                    "tcp_id": self.tcp_id,
                    "body": {
                        "x": self.arrow_rect.x + game.mo,
                        "y": self.arrow_rect.y + game.mo,
                        "angle": self.angle,
                    },
                }
            )
        )

    def set_weapon(self, weapon):
        self.weapon_anim = 0
        weapon = int(weapon)
        self.weapon_hud_tex = gtex.mask_object_textures[weapon]
        self.weapon_hud_rect = self.weapon_hud_tex.get_rect(
            bottomright=(display.width - 160, display.height - 10)
        ).scale_by(4)
        weapon = str(weapon)
        if self.weapons.count(None) == 0:  # no empty weapon slots
            self.weapons[self.weapon_index] = weapon
            self.ammos[self.weapon_index] = weapon_data[weapon]["ammo"]
            self.mags[self.weapon_index] = weapon_data[weapon]["mag"]
        elif self.weapons.count(None) == 1:  # one empty weapon slots
            self.weapons[1] = weapon
            self.ammos[1] = weapon_data[weapon]["ammo"]
            self.mags[1] = weapon_data[weapon]["mag"]
            self.weapon_index = 1
        else:  # two empty weapon slots
            self.weapons[0] = weapon
            self.ammos[0] = weapon_data[weapon]["ammo"]
            self.mags[0] = weapon_data[weapon]["mag"]
        hud.update_weapon_general(self)

    def update(self):
        if game.multiplayer:
            self.send_location()

            if client_udp.current_message:
                msg = json.loads(client_udp.current_message)[self.tcp_id]
                self.deaths = msg["deaths"]
                self.kills = msg["kills"]
                self.score = msg["score"]

            for message in client_tcp.queue.copy():
                if message.startswith("take_damage|"):
                    split = message.split("|")
                    self.health = max(self.health - int(split[2]), 0)
                    hud.update_health(self)

                    if self.health <= 0:
                        client_tcp.req(f"kill|{self.tcp_id}")

                        score_inc = 25
                        self.score += score_inc
                        client_tcp.req(f"inc_score|{split[1]}|{score_inc}")

                        game.set_state(States.MAIN_MENU)

                    client_tcp.queue.remove(message)

                elif message.startswith("inc_score|"):
                    self.score += int(message.split("|")[1])
                    client_tcp.queue.remove(message)

                elif message == f"kill|{self.tcp_id}":
                    game.set_state(States.MAIN_MENU)
                    client_tcp.queue.remove(message)
                    return

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
        self.id: str = id_
        self.x = int(game.tile_size * rand(0, game.map_width - 3))
        self.y = int(game.tile_size * rand(0, game.map_height - 3))
        self.w = 8
        self.h = 8
        self.score = 500
        self.kills = 0
        self.deaths = 0
        self.angle = radians(-90) # TODO: Implement enemy direction
        self.indicator = imgload(
            "client", "assets", "images", "minimap", "enemy_indicator.png"
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
        self.health = 100  # currently not being updated
        self.name: str = None  # this doesn't work yet
        self.audio_channels = [pygame.mixer.find_channel() for _ in range(2)]

    def init_image(self, surf: pygame.Surface):
        self.image = Texture.from_surface(
            display.renderer,
            surf.subsurface(0, 0, surf.get_width() / 4, surf.get_height())
        )

    def draw(self):
        if game.multiplayer:
            if client_udp.current_message:
                message = json.loads(client_udp.current_message)
                if self.id not in message:
                    self.die()
                    return
                self.indicator_rect.x = message[self.id]["x"]
                self.indicator_rect.y = message[self.id]["y"]
                self.angle = message[self.id]["angle"]
                self.deaths = message[self.id]["deaths"]
                self.kills = message[self.id]["kills"]
                self.score = message[self.id]["score"]

        self.rendering = False
        # draw_rect(Colors.RED, self.indicator_rect)
        display.renderer.blit(self.indicator, self.indicator_rect)

    def update(self):
        if game.multiplayer:
            if self.health <= 0:
                client_tcp.req(f"kill|{self.id}")

            for message in client_tcp.queue.copy():
                if message in (f"kill|{self.id}", f"quit|{self.id}"):
                    self.die()

                    client_tcp.queue.remove(message)
                    return

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
            wall_height = (game.projection_dist / self.dist_px * display.height / 2) / (game.fov / 60)  # maths
            centery = display.height / 2 + player.view_yoffset + wall_height * 0.2
            height = wall_height * 0.8  # maths
            width = height / self.image.height * self.image.width
            # rects
            og_width, og_height = 232 / 2, 400 / 2
            head_w_ratio = 84 / og_width
            head_h_ratio = 88 / og_height
            torso_w_ratio = 92 / og_width
            torso_h_ratio = 148 / og_height
            legs_w_ratio = 100 / og_width
            legs_h_ratio = 168 / og_height
            shoulder_w_ratio = 28 / og_width
            shoulder_h_ratio = 84 / og_height
            arm_w_ratio = 44 / og_width
            arm_h_ratio = 200 / og_height
            # whole body
            self.rect = pygame.Rect(0, 0, width, height)
            self.rect.center = (centerx, centery)
            # head
            self.head_rect = pygame.Rect(
                0, 0, head_w_ratio * width, head_h_ratio * height
            )
            self.head_rect.midtop = (self.rect.centerx, self.rect.top)
            # torso
            self.torso_rect = pygame.Rect(
                0, 0, torso_w_ratio * width, torso_h_ratio * height
            )
            self.torso_rect.midtop = (self.rect.centerx, self.head_rect.bottom)
            # legs
            self.legs_rect = pygame.Rect(
                0, 0, legs_w_ratio * width, legs_h_ratio * height
            )
            self.legs_rect.midtop = (self.rect.centerx, self.torso_rect.bottom)
            # shoulders
            self.shoulder1_rect = pygame.Rect(
                0, 0, shoulder_w_ratio * width, shoulder_h_ratio * height
            )
            self.shoulder1_rect.topright = self.torso_rect.topleft
            self.shoulder2_rect = pygame.Rect(
                0, 0, shoulder_w_ratio * width, shoulder_h_ratio * height
            )
            self.shoulder2_rect.topleft = self.torso_rect.topright
            # arms
            self.arm1_rect = pygame.Rect(
                0, 0, arm_w_ratio * width, arm_h_ratio * height
            )
            self.arm1_rect.topright = self.shoulder1_rect.topleft
            self.arm2_rect = pygame.Rect(
                0, 0, arm_w_ratio * width, arm_h_ratio * height
            )
            self.arm2_rect.topleft = self.shoulder2_rect.topright
            # rest
            display.renderer.blit(self.image, self.rect)
            draw_rect(Colors.YELLOW, self.rect)
            fill_rect(Colors.ORANGE, self.head_rect)
            fill_rect(Colors.RED, self.shoulder1_rect)
            fill_rect(Colors.GREEN, self.legs_rect)
            fill_rect(Colors.BLUE, self.torso_rect)
            fill_rect(Colors.PINK, self.arm1_rect)

            """
            draw_rect(Colors.YELLOW, self.rect)
            draw_rect(Colors.ORANGE, self.head_rect)
            draw_rect(Colors.LIGHT_BLUE, self.torso_rect)
            draw_rect(Colors.GREEN, self.shoulder1_rect)
            draw_rect(Colors.GREEN, self.shoulder2_rect)
            draw_rect(Colors.BLUE, self.arm1_rect)
            draw_rect(Colors.BLUE, self.arm2_rect)
            draw_rect(Colors.PINK, self.legs_rect)
            """
            self.rendering = True

    def regenerate(self):
        if self.regenerating and ticks() - self.last_hit >= 70:
            self.regenerating = False

    def hit(self, mult, melee=False):
        self.last_hit = ticks()
        self.regenerating = True
        damage = int(weapon_data[player.weapon if not melee else "2"]["damage"] * mult)
        if game.multiplayer:
            client_tcp.req(f"damage|{self.id}|{damage}")
        if self.health <= 0:
            self.update()  # for dying

    def die(self):
        try:
            del leaderboard.texs[self.id]
            enemies.remove(self)
        except:
            pass


class Crosshair:
    def __init__(self):
        self.w = 3  # width
        self.l = 20  # length
        self.target_offset = self.o = 50  # self.o is offset
    
    @property
    def radius(self):
        return self.bottom[1] - display.height / 2

    def update(self):
        if game.target_zoom > 0:
            self.target_offset = 4
            self.l = 10
            self.zooming_mult = 0.15
        else:
            self.l = 15
            if player.moving:
                self.target_offset = 60
            else:
                self.target_offset = 20
            self.zooming_mult = 0.05
        self.o += (self.target_offset - self.o) * self.zooming_mult
        self.center = (display.width / 2 - self.w / 2, display.height / 2 - self.w / 2, self.w, self.w)
        self.right = (display.width / 2 + self.w / 2 + self.o, display.height / 2 - self.w / 2, self.l, self.w)
        self.left = (display.width / 2 - self.w / 2 - self.o - self.l, display.height / 2 - self.w / 2, self.l, self.w)
        self.bottom = (display.width / 2 - self.w / 2, display.height / 2 + self.w / 2 + self.o, self.w, self.l)
        self.top = (display.width / 2 - self.w / 2, display.height / 2 - self.w / 2 - self.o - self.l, self.w, self.l)
        fill_rect(Colors.WHITE, self.center)
        fill_rect(Colors.WHITE, self.right)
        fill_rect(Colors.WHITE, self.left)
        fill_rect(Colors.WHITE, self.bottom)
        fill_rect(Colors.WHITE, self.top)


class Shot:
    def __init__(self, pos):
        self.x, self.y = pos
        self.r = 2
        self.alpha = 255
    
    def update(self):
        if self.alpha < 0:
            shots.remove(self)
            return
        fill_rect([0, 0, 0, self.alpha], (self.x - self.r, self.y - self.r, self.r * 2, self.r * 2))
        self.alpha -= 15 * game.dt


crosshair = Crosshair()
cursor.enable()
# player_selector.set_all_skins()
player_selector = PlayerSelector()
player: Player = None  # initialization is in game.set_state
hud: HUD = None  # same as above
game = Game()
gtex = GlobalTextures()
leaderboard = Leaderboard()
enemies: list[EnemyPlayer] = []
feed: list[tuple[Texture, int]] = []
shots: list[Shot] = []
clock = pygame.time.Clock()
joystick: pygame.joystick.JoystickType = None

crosshair_tex = imgload("client", "assets", "images", "hud", "crosshair.png", scale=3)
crosshair_rect = crosshair_tex.get_rect(center=(display.center))

wasd_image = imgload("client", "assets", "images", "controls", "WASD.png", scale=0.5)
e_image = imgload("client", "assets", "images", "controls", "E.png", scale=0.5)
q_image = imgload("client", "assets", "images", "controls", "Q.png", scale=0.5)
tab_image = imgload("client", "assets", "images", "controls", "TAB.png", scale=0.5)
controls_images = [wasd_image, e_image, q_image, tab_image]

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
        display.height / 2 + 48 * -1,
        "Field of view",
        game.set_fov,
        action_arg=10,
        is_slider=True,
        slider_display=game.get_fov,
    ),
    Button(
        80,
        display.height / 2 + 48 * 0,
        "Sensitivity",
        game.set_sens,
        action_arg=10,
        is_slider=True,
        slider_display=game.get_sens,
    ),
    Button(
        80,
        display.height / 2 + 48 * 1,
        "Resolution",
        game.set_res,
        action_arg=1,
        is_slider=True,
        slider_display=game.get_res,
    ),
    Button(
        80,
        display.height / 2 + 48 * 2,
        "Volume",
        game.set_volume,
        action_arg=5,
        is_slider=True,
        slider_display=game.get_volume,
    ),
    Button(
        80,
        display.height / 2 + 48 * 3,
        "Max FPS",
        game.set_max_fps,
        action_arg=1,
        is_slider=True,
        slider_display=game.get_max_fps,
    ),
    Button(
        80,
        display.height / 2 + 48 * 4,
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
            or username_input.text == "",
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
            "Controls",
            lambda: game.set_state(States.CONTROLS),
        ),
        Button(
            80,
            display.height / 2 + 48 * 3,
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
        *main_settings_buttons[0:6],
        Button(
            80,
            display.height / 2 + 48 * 4,
            "Return to main menu",
            lambda: game.set_state(States.MAIN_MENU),
        ),
        Button(
            80,
            display.height / 2 + 48 * 5,
            "Back",
            lambda: game.set_state(game.previous_state),
            font_size=48,
        ),
    ],
    States.PLAY: [],
    States.CONTROLS: [
        Button(
        80,
        display.height / 2 + 48 * 5,
        "Back",
        lambda: game.set_state(game.previous_state),
        font_size=48,
        ),
    ], 
}
prim_skin_button = all_buttons[States.MAIN_MENU][5]
sec_skin_button = all_buttons[States.MAIN_MENU][6]
unleash_button = all_buttons[States.MAIN_MENU][1]
player_selector.init()

username_input = UserInput(
    player_selector.rect.centerx, player_selector.rect.y - 30, 40, Colors.WHITE
)


class Hue:
    def __init__(self, color, alpha):
        self.surf = pygame.Surface((display.width, display.height), pygame.SRCALPHA)
        self.surf.fill(color)
        self.surf.set_alpha(alpha)
        self.tex = Texture.from_surface(display.renderer, self.surf)
        self.rect = self.surf.get_rect()


darken_game = Hue(Colors.BLACK, 80)
redden_game = Hue(Colors.RED, 20)

menu_wall_index = 0
menu_wall_texs = imgload(
    "client",
    "assets",
    "images",
    "menu",
    "wallpaper",
    "wallpaper.png",
    scale=1,
    frames=8,
)

floor_tex = imgload("client", "assets", "images", "3d", "floor.png")
joystick_button_sprs = imgload(
    "client", "assets", "images", "hud", "buttons.png", scale=4, frames=4
)
joystick_button_rect = joystick_button_sprs[0].get_rect()


def add_enemy(address: str, data: Dict[str, Any]) -> None:
    new_enemy = EnemyPlayer(id_=address)
    new_enemy.health = data["health"]
    new_enemy.name = data["name"]

    [channel.set_volume(game.volume) for channel in new_enemy.audio_channels]
    prim = player_selector.color_keys[data["prim_color"]]
    sec = player_selector.color_keys[data["sec_color"]]
    surf = player_selector.database[f"{prim}_{sec}"]
    new_enemy.image = Texture.from_surface(
        display.renderer,
        surf.subsurface(0, 0, surf.get_width() / 4, surf.get_height())
    )

    enemies.append(new_enemy)
    leaderboard.texs[new_enemy.id] = (text2tex(new_enemy.name, 32), None)


def render_floor():
    fill_rect(
        Colors.BROWN,
        (
            0,
            display.height / 2 + player.view_yoffset,
            display.width,
            display.height / 2 - player.view_yoffset,
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
        game.dt = clock.tick(game.get_max_fps()) / (1 / 60 * 1000)
        player.process_shot = False
        player.process_melee = False

        # Global TCP events
        if game.multiplayer:
            for message in client_tcp.queue.copy():
                split = message.split("|")
                match split[0]:
                    case "init_player":
                        add_enemy(split[1], json.loads(split[2]))

                        client_tcp.queue.remove(message)

                    case "feed":
                        global feed
                        feed.append((text2tex(split[1], 32), ticks()))

                        client_tcp.queue.remove(message)

                    case "init_res":
                        res = json.loads(split[1])
                        for e_id, data in res.items():
                            add_enemy(e_id, data)

                        client_tcp.queue.remove(message)

                    case "shoot":
                        for enemy in enemies.copy():
                            if enemy.id == split[1]:
                                distance = hypot(
                                    player.arrow_rect.x - int(split[3]),
                                    player.arrow_rect.y - int(split[4]),
                                )

                                # Maybe make this a little better
                                if distance > game.tile_size * 2:
                                    volume = game.volume ** 2 / ((distance - game.tile_size * 2) / game.tile_size * 4)
                                else:
                                    volume = 1

                                # enemy.audio_channels[0].set_volume(volume)
                                # # enemy.audio_channels[0].play(
                                # #     weapon_data[split[2]]["shot_sound"]
                                # # )

                        client_tcp.queue.remove(message)

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
                                player.angle += (
                                    (event.rel[0] * game.sens / 100_000)
                                    * 100
                                    / game.fov
                                )
                                player.angle %= 2 * pi

                            # if/elif are for vertical mouse wrap
                            if ypos > display.height - 20:
                                pygame.mouse.set_pos(xpos, 20)
                            elif ypos < 20:
                                pygame.mouse.set_pos(xpos, display.height - 21)
                            else:
                                player.bob -= (
                                    (event.rel[1] * game.sens / 60) * 100 / game.fov
                                )
                                player.bob = min(player.bob, display.height * 1.5)
                                player.bob = max(player.bob, -display.height * 1.5)

                case pygame.MOUSEBUTTONDOWN:
                    if game.state == States.PLAY:
                        if event.button == 1:
                            player.process_shot = True
                        if event.button == 3:
                            pass

                case pygame.MOUSEBUTTONUP:
                    if game.state == States.PLAY:
                        if event.button == 3:
                            pass

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

                        case pygame.K_q:
                            player.process_melee = True

                case pygame.JOYDEVICEADDED:
                    joystick = pygame.joystick.Joystick(event.device_index)

                case pygame.JOYBUTTONDOWN:
                    if event.button == Joymap.CROSS:
                        # player.jump() implement
                        ...

            for button in current_buttons:
                button.process_event(event)

        display.renderer.clear()

        if game.state in (States.MAIN_MENU, States.MAIN_SETTINGS, States.CONTROLS):
            # fill_rect(Colors.BLACK, (0, 0, display.width, display.height))
            global menu_wall_index
            display.renderer.blit(
                menu_wall_texs[int(menu_wall_index)],
                pygame.Rect(0, 0, display.width, display.height),
            )
            menu_wall_index += 0.13 * game.dt
            if menu_wall_index > 7:
                menu_wall_index = 0

        if game.state == States.MAIN_MENU:
            player_selector.update()
            username_input.update()
        
        if game.state == States.CONTROLS:
            controls_outline = pygame.Rect(display.width/2 - 400, 100, 800, 750)
            controls_black_surf = pygame.Surface(controls_outline.size, pygame.SRCALPHA)
            controls_black_surf.fill((0, 0, 0, 120))
            controls_black_tex = Texture.from_surface(display.renderer, controls_black_surf)
            display.renderer.blit(controls_black_tex, controls_outline)
            index = 1
            for img in controls_images:
                display.renderer.blit(img, img.get_rect(topleft= (display.width/2 - 350, 150 * index + 50)))
                text = ""
                match index:
                    case 1:
                        text = "to move"
                    case 2:
                        text = "to buy and switch weapons"
                    case 3:
                        text = "to use melee"
                    case 4:
                        text = "to show leaderboard"
                write("center", 
                text, 
                v_fonts[40], 
                Colors.WHITE, 
                display.width/2 + 75, 
                150 * index + 135,
                )
                index += 1

        if game.state in (States.PLAY, States.PLAY_SETTINGS):
            fill_rect(
                Colors.DARK_GRAY,
                (0, 0, display.width, display.height / 2 + player.view_yoffset),
            )
            # display.renderer.blit(sky_tex, sky_rect)
            fill_rect(
                Colors.BROWN,
                (
                    0,
                    display.height / 2 + player.view_yoffset,
                    display.width,
                    display.height / 2 - player.view_yoffset,
                ),
            )

            player.update()
            if game.should_render_map:
                player.draw()
                if game.multiplayer:
                    for enemy in enemies:
                        enemy.update()

            hud.update()

            display.renderer.blit(redden_game.tex, redden_game.rect)
            for shot in shots:
                shot.update()

        if game.state == States.PLAY:
            game.zoom += (game.target_zoom - game.zoom) * game.zoom_speed
            # display.renderer.blit(crosshair_tex, crosshair_rect)
            crosshair.update()

            if pygame.key.get_pressed()[pygame.K_TAB]:
                leaderboard.update()

        if game.state == States.PLAY_SETTINGS:
            display.renderer.blit(darken_game.tex, darken_game.rect)

        for button in current_buttons:
            button.update()

        if cursor.enabled:
            cursor.update()

        write(
            "topright",
            f"{int(clock.get_fps())} FPS",
            v_fonts[20],
            Colors.WHITE,
            display.width - 5,
            5,
        )

        display.renderer.present()

    sys.exit()
