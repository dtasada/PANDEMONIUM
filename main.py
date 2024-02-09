import pygame
from pygame._sdl2.video import Window, Renderer, Texture, Image
import sys
from math import sin, cos, tan, atan2, pi


def fill_rect(renderer, color, rect):
    renderer.draw_color = color
    renderer.fill_rect(rect)
        

def draw_line(renderer, color, p1, p2):
    renderer.draw_color = color
    renderer.draw_line(p1, p2)
        

def angle_to_vel(angle, speed=1):
    return cos(angle) * speed, sin(angle) * speed


class Display:
    def __init__(self, width, height, title):
        self.width, self.height, self.title = width, height, title
        self.window = Window(size=(self.width, self.height))
        self.renderer = Renderer(self.window)


class Game:
    def __init__(self):
        self.running = __name__ == "__main__"
        self.fps = 60
        self.sens = 200
        self.map = [
            [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
            [1, 0, 0, 0, 0, 0, 1, 1, 0, 1],
            [1, 0, 0, 0, 0, 0, 0, 0, 0, 1],
            [1, 0, 0, 1, 0, 0, 0, 0, 0, 1],
            [1, 0, 0, 0, 0, 1, 0, 1, 0, 1],
            [1, 0, 0, 0, 0, 0, 0, 1, 0, 1],
            [1, 0, 0, 1, 0, 0, 0, 0, 0, 1],
            [1, 0, 1, 0, 0, 0, 0, 0, 0, 1],
            [1, 0, 0, 0, 0, 0, 0, 0, 0, 1],
            [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        ]


class Player:
    def __init__(self):
        self.x = 10
        self.y = 10
        self.w = 10
        self.h = 10
        self.color = (160, 160, 160, 255)
        self.angle = 0
        
    def draw(self):
        fill_rect(display.renderer, self.color, (self.x, self.y, self.w, self.h))
    
    def keys(self):
        vmult = 1
        keys = pygame.key.get_pressed()
        xvel = yvel = 0
        if keys[pygame.K_w]: xvel, yvel = angle_to_vel(self.angle, vmult)
        if keys[pygame.K_a]: xvel, yvel = angle_to_vel(self.angle - pi / 2, vmult)
        if keys[pygame.K_s]: xvel, yvel = angle_to_vel(self.angle + pi, vmult)
        if keys[pygame.K_d]: xvel, yvel = angle_to_vel(self.angle + pi / 2, vmult)
        p1 = (self.x + self.w / 2, self.y + self.h / 2)
        p2 = (p1[0] + xvel * 100, p1[1] + yvel * 100)

        draw_line(display.renderer, (255, 255, 0, 255), p1, p2)

        self.x += xvel
        self.y += yvel

    def update(self):
        self.keys()
        self.draw()
            

pygame.init()
display = Display(1280, 720, "gaem")
player = Player()
game = Game()
clock = pygame.time.Clock()

while game.running:
    clock.tick(game.fps)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            game.running = False

        elif event.type == pygame.MOUSEMOTION:
            player.angle += event.rel[0] / game.sens
            player.angle %= 2 * pi

    display.renderer.clear()
    fill_rect(display.renderer, (40, 40, 40, 255), (0, 0, display.width, display.height))

    player.update()

    display.renderer.present()

pygame.quit()
sys.exit()
