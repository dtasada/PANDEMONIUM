import pygame
import sys
import json
import os

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
        self.resolution = 2
        self.ray_density = int(display.width * (self.resolution / 4))
        self.target_zoom = self.zoom = 0
        self.zoom_speed = 0.4
        self.projection_dist = 32 / tan(radians(self.fov / 2))
        self.rendered_enemies = 0
        # map
        self.maps = {}
        for file in os.listdir(Path("client", "assets", "maps")):
            self.maps[file.split("-")[0]] = {
                "walls": load_map_from_csv(
                    Path("client", "assets", "maps", f"{file.split('-')[0]}-walls.csv")
                ),
                "weapons": load_map_from_csv(
                    Path(
                        "client", "assets", "maps", f"{file.split('-')[0]}-weapons.csv"
                    ),
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
        self.resolution += amount
        if self.resolution > 4:
            self.resolution = 4
        elif self.resolution < 1:
            self.resolution = 1

        self.ray_density = int(display.width * (self.resolution / 4))


class GlobalTextures:
    def __init__(self):
        self.x = game.tile_size * 8
        self.y = game.tile_size * 8
        self.w = 8
        self.h = 8
        self.id = None
        self.color = Colors.WHITE
        self.angle = -1.5708
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
                imgload(
                    "client", "assets", "images", "objects", file_name_with_ext + ".png"
                )
                if file_name_with_ext is not None
                else None
            )
            for file_name_with_ext in weapon_names
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
                                file_name_with_ext + ".png",
                            )
                        ),
                        Colors.YELLOW,
                    ),
                )
                if file_name_with_ext is not None
                else None
            )
            for file_name_with_ext in weapon_names
        ]
        #
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
    
    def update(self):
        if self.health_tex is not None:
            display.renderer.blit(self.health_tex, self.health_rect)
        if self.ammo_tex is not None:
            display.renderer.blit(self.ammo_tex, self.ammo_rect)
            w, h = 3, 25
            for yo in range(weapon_data[player.weapon]["mag"]):
                color = Colors.WHITE if yo < player.mag else Colors.GRAY
                yo = -yo * w * 4
                fill_rect(color, (
                    self.ammo_rect.x + yo - 15,
                    self.ammo_rect.centery - h / 2 + 2,
                    w,
                    h,
                    )
                )

        if self.weapon_name_tex is not None:
            display.renderer.blit(self.weapon_name_tex, self.weapon_name_rect)
        if self.weapon_tex is not None:
            display.renderer.blit(self.weapon_tex, self.weapon_rect)

    def update_weapon_general(self, player):
        self.update_weapon_tex(player)
        self.update_ammo(player)
        self.update_weapon_name(player)

    def update_health(self, player):
        self.health_tex, self.health_rect = write(
            "bottomleft",
            f"HP: {player.health}",
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
            display.height - 4
        )
        
    
    def update_weapon_name(self, player):
        self.weapon_name_tex, self.weapon_name_rect = write(
            "bottomright",
            weapon_names[int(player.weapon)].title(),
            v_fonts[32],
            Colors.WHITE,
            display.width - 16,
            self.ammo_rect.y
        )
    
    def update_weapon_tex(self, player):
        self.weapon_tex = gtex.mask_object_textures[int(player.weapon)]
        self.weapon_rect = self.weapon_tex.get_rect()
        m = 3
        self.weapon_rect.inflate_ip(self.weapon_rect.width * m, self.weapon_rect.height * m)
        self.weapon_rect.center = (display.width - 60, display.height - 40)


class Player:
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

        self.bob = 0
        self.to_equip = None
        # weapon
        self.weapon_hud_tex = self.weapon_hud_rect = None
        self.last_shot = ticks()

        hud.update_health(self)

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

    @property
    def health(self):
        # TODO: Server call
        return 100

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
            weapon_rect.midbottom = (display.width / 2, display.height + self.weapon_yoffset)
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
                te = self.enemies_to_render[0]
                if te.dist_px > dist_px:
                    te.render()
                    del self.enemies_to_render[0]
            # render the texture after the (farther away) enemy
            tex.color = color
            display.renderer.blit(tex, dest, area)
        # render the remaining enemies
        for te in self.enemies_to_render:
            te.render()
        for te in self.enemies_to_render:
            te.render()

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

        for te in test_enemies:
            dy = te.indicator_rect.centery - self.rect.centery
            dx = te.indicator_rect.centerx - self.rect.centerx
            te.angle = degrees(atan2(dy, dx))
            te.dist_px = hypot(dy, dx)
        for te in test_enemies:
            if not self.enemies_to_render:
                self.enemies_to_render.append(te)
            else:
                for index, enemy in enumerate(test_enemies):
                    if te.dist_px > enemy.dist_px:
                        self.enemies_to_render.insert(index, te)
                        break
                else:
                    self.enemies_to_render.append(te)

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
                    if player.weapon is not None:
                        if shoot_auto or self.process_shot:
                            if self.mag == 0:
                                self.reload()
                            else:
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
            for te in test_enemies:
                if te.rendering:
                    if not te.regenerating:
                        if te.rect.collidepoint(display.center):
                            te.hit()
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
        data = {
            "x": self.arrow_rect.x + game.mo,
            "y": self.arrow_rect.y + game.mo,
            "angle": self.angle,
        }
        data = json.dumps(data)
        client_udp.req(data)

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
            if not self.id and client_udp.current_message:
                message = json.loads(client_udp.current_message)
                self.id = message["id"]
        self.rays = []
        self.walls_to_render = []
        self.enemies_to_render = []
        self.keys()
        # updates
        pass
        # 
        # Thread(client_tcp.req, args=(self.health,)).start()
        for data in self.rays:
            ray, _ = data
            p1 = (ray[0][0] + game.mo, ray[0][1] + game.mo)
            p2 = (ray[1][0] + game.mo, ray[1][1] + game.mo)
            draw_line(Colors.GREEN, p1, p2)
        player.display_weapon()


class EnemyPlayer:
    def __init__(self, id_):
        self.id_ = id_
        self.x = game.tile_size * 8
        self.y = game.tile_size * 8
        self.w = 8
        self.h = 8
        self.angle = -1.5708
        self.arrow_surf = pygame.image.load(
            Path("client", "assets", "images", "minimap", "player_arrow.png")
        )
        self.rect = pygame.FRect((self.x, self.y, self.w, self.h))
        self.arrow_img = Image(Texture.from_surface(display.renderer, self.arrow_surf))
        self.indicator_img = imgload(
            "client", "assets", "images", "enemy_indicator.png"
        )

        self.indicator_rect = self.indicator_img.get_rect()
        self.arrow_rect = self.arrow_surf.get_rect(middle=(64, 64))

    def draw(self):
        arrow = self.arrow_img
        arrow.angle = degrees(self.angle)
        draw_rect(Colors.GREEN, self.arrow_rect)
        display.renderer.blit(
            self.indicator_img,
            pygame.Rect(self.arrow_rect.x, self.arrow_rect.y, *self.arrow_rect.size),
        )

    def update(self):
        if client_udp.current_message:
            message = json.loads(client_udp.current_message)
            if self.id_ not in message:
                enemy_players.remove(self)
                enemy_players_addr.remove(self.id_)
                return
            self.rect.x = message[self.id_]["x"]
            self.rect.y = message[self.id_]["y"]
            self.angle = message[self.id_]["angle"]
        self.draw()


class TestEnemy:
    def __init__(self):
        self.x = int(game.tile_size * rand(0, game.map_width - 3))
        self.y = int(game.tile_size * rand(0, game.map_height - 3))
        self.w = 8
        self.h = 8
        self.angle = -1.5708
        self.indicator = imgload(
            "client", "assets", "images", "minimap", "player_arrow.png"
        )
        self.indicator.color = Colors.ORANGE
        self.indicator_rect = pygame.Rect((0, 0, 16, 16))
        self.indicator_rect.center = (self.x, self.y)
        self.last_hit = ticks()
        self.regenerating = False
        self.rendering = False
        self.images = imgload("client", "assets", "images", "3d", "player.png", frames=4)
        self.image = self.images[0]
        self.color = [rand(0, 255) for _ in range(3)] + [255]
        self.image.color = self.color
        self.hp = 10

    def draw(self):
        self.rendering = False
        draw_rect(Colors.RED, self.indicator_rect)
        display.renderer.blit(self.indicator, self.indicator_rect)

    def update(self):
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
            perc = (diff1) / (diff1 + diff2)
            centerx = perc * display.width
            centery = display.height / 2 + player.bob
            height = game.projection_dist / self.dist_px * display.height / 2 # maths
            width = height / self.image.height * self.image.width
            self.rect = pygame.Rect(0, 0, width, height)
            self.rect.center = (centerx, centery)
            display.renderer.blit(self.image, self.rect)
            self.rendering = True

    def regenerate(self):
        if self.regenerating and ticks() - self.last_hit >= 70:
            self.regenerating = False
            self.image.color = self.color

    def hit(self):
        self.image.color = Colors.RED
        self.last_hit = ticks()
        self.regenerating = True
        self.hp -= 1
        if self.hp == 0:
            test_enemies.remove(self)
            for _ in range(2):
                test_enemies.append(TestEnemy())


cursor.enable()
game = Game()
test_enemies = [TestEnemy()]
hud = HUD()
player = Player()
gtex = GlobalTextures()
enemy_players = []
enemy_players_addr = []
clock = pygame.time.Clock()
joystick = None

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
    States.PLAY: [],
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

floor_tex = imgload("client", "assets", "images", "3d", "floor.png")
joystick_button_sprs = imgload(
    "client", "assets", "images", "hud", "buttons.png", scale=4, frames=4
)
joystick_button_rect = joystick_button_sprs[0].get_rect()


def check_new_players():
    if client_udp.current_message:
        message = json.loads(client_udp.current_message)
        for addr in message:
            if addr not in enemy_players_addr and addr != "id":
                enemy_players_addr.append(addr)
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

    game.multiplayer = multiplayer
    if multiplayer:
        client_udp = Client("udp")
        client_tcp = Client("tcp")
        Thread(target=client_udp.receive, daemon=True).start()
        Thread(target=client_tcp.receive, daemon=True).start()

    while game.running:
        clock.tick(game.fps)
        player.process_shot = False

        for event in pygame.event.get():
            match event.type:
                case pygame.QUIT:
                    game.running = False
                    if multiplayer:
                        client_tcp.req(f"quit-{player.id}")
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
                        player.process_shot = True
                        # if event.button == 1:
                        #     game.target_zoom = 30
                        #     game.zoom = 0

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
                        
                        case pygame.K_r:
                            player.reload()

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
                for te in test_enemies:
                    te.update()
                if game.should_render_map:
                    player.draw()
                    if multiplayer:
                        check_new_players()
                        for enemy in enemy_players:
                            enemy.update()
                
                hud.update()

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
