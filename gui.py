import pygame, os
from player import *

width = 500
height = 500

mon_size = 150

size = (width, height)
screen = pygame.display.set_mode(size)

# gui colors
white = (255, 255, 255)
black = (0, 0, 0)
green = (16, 177, 14)
yellow = (222, 189, 57)
gold = (242, 219, 152)
red = (255, 0, 0)
gray = (46, 52, 64)

# type colors
col_normal = (159, 161, 159)
col_fighting = (255, 128, 0)
col_flying = (129, 185, 239)
col_poison = (145, 65, 203)
col_ground = (145, 81, 33)
col_rock = (175, 169, 129)
col_bug = (145, 161, 25)
col_ghost = (112, 65, 112)
col_steel = (96, 161, 184)
col_fire = (230, 40, 41)
col_water = (41, 128, 239)
col_grass = (63, 161, 41)
col_electric = (250, 192, 0)
col_psichic = (239, 65, 121)
col_ice = (63, 216, 255)
col_dragon = (80, 96, 225)
col_dark = (80, 65, 63)
col_fairy = (239, 112, 239)

class TextBox:
    def __init__(self, x, y, text, player, enemy):
        self.x = x
        self.y = y
        self.clicked = False
        self.text = text
        self.font = pygame.font.SysFont(None, 24)
        #rendered_text = self.font.render(text, True, black)

    def blit_text(self, box, text, pos):
        words = [word.split(' ') for word in text.splitlines()]
        space = self.font.size(' ')[0]
        max_width = box.width/2
        height = box.height

        x, y = pos
        
        for line in words:
            for word in line:
                word_surface = self.font.render(word, 1, black)
                word_width, word_height = word_surface.get_size()
                if x + word_width >= max_width:
                    x = pos[0]
                    y += word_height
                screen.blit(word_surface, (x, y))
                x += word_width + space
            x = pos[0]
            y += word_height

    def draw(self, text):
        border = pygame.Rect(self.x, self.y, 500, 120)
        inner = pygame.Rect(self.x+5, self.y+5, 490, 110)
        pygame.draw.rect(screen, black, border)
        pygame.draw.rect(screen, white, inner)
        #screen.blit(self.rendered_text, (self.x+10, self.y+10))
        self.blit_text(inner, text, (self.x+10, self.y+10))
    

class Button:
    def __init__(self, x, y, text, player, enemy):
        self.x = x
        self.y = y
        self.clicked = False
        self.text = text
        self.font = pygame.font.SysFont(None, 24)
        self.rendered_text = self.font.render(text, True, white)

        self.player = player
        self.enemy = enemy

    def draw(self):
        rect = pygame.Rect(self.x, self.y, 50, 15)
        pygame.draw.rect(screen, black, rect)
        screen.blit(self.rendered_text, (self.x, self.y))

        mouse = pygame.mouse.get_pos()
        #print(mouse)

        if rect.collidepoint(mouse):
            if pygame.mouse.get_pressed()[0] == 1 and self.clicked == False:
                self.player_mon.atk(self.enemy)
                self.clicked = True

        if pygame.mouse.get_pressed()[0] == 0:
            self.clicked = False
        
class GameWindow:
    def __init__(self, player: Trainer = None, enemy: Trainer = None, sound=True):
        pygame.init()
        
        self.font = pygame.font.SysFont(None, 24)
        self.hp_text = self.font.render('HP :', True, gold)
        self.lv_text = self.font.render('L. :', True, black)

        self.player = player
        self.player_mon = self.player.in_battle
        self.player_mon_name = self.font.render(self.player_mon.name, True, black)
        self.player_mon_sprite = pygame.image.load(os.path.join('assets/sprites/back/{id}.png'.format(id = self.player_mon.id)))
        self.player_mon_sprite = pygame.transform.scale(self.player_mon_sprite, (mon_size, mon_size))
        self.hp_player = [self.player_mon.hp, self.player_mon.max_hp]
        self.hp_player_text = self.font.render(str(self.hp_player[0]) + '/' + str(self.hp_player[1]), True, black)
        self.lv_player_text = self.font.render(str(self.player_mon.level), True, black)
        self.enemy_type1_text = self.font.render('FIR', True, white)

        self.enemy = enemy
        self.enemy_mon = self.enemy.in_battle
        self.enemy_mon_name = self.font.render(self.enemy_mon.name, True, black)
        self.enemy_mon_sprite = pygame.image.load(os.path.join('assets/sprites/front/{id}.png').format(id = self.enemy_mon.id))
        self.enemy_mon_sprite = pygame.transform.scale(self.enemy_mon_sprite, (mon_size, mon_size))
        self.hp_enemy = [self.enemy_mon.hp, self.enemy_mon.max_hp]
        self.hp_enemy_text = self.font.render(str(self.hp_enemy[0]) + '/' + str(self.hp_enemy[1]), True, black)
        self.lv_enemy_text = self.font.render(str(self.enemy_mon.level), True, black)
        self.enemy_type1_text = self.font.render('GRA', True, white)
        self.enemy_type2_text = self.font.render('PSN', True, white)

        pygame.mixer.music.load(os.path.join('assets/sounds/battle.mp3'))
        if sound == True:
            pygame.mixer.music.play(-1)

        self.textbox = TextBox(0, 380, 'Prova testo', self.player, self.enemy)
        self.attack_button = Button(250, 400, 'Attack', self.player, self.enemy)
    
    def update_text(self):
        self.hp_player = [self.player_mon.hp, self.player_mon.max_hp]
        self.hp_player_text = self.font.render(str(self.hp_player[0]) + '/' + str(self.hp_player[1]), True, black)

        self.hp_enemy = [self.enemy_mon.hp, self.enemy_mon.max_hp]
        self.hp_enemy_text = self.font.render(str(self.hp_enemy[0]) + '/' + str(self.hp_enemy[1]), True, black)

    def draw(self):
        self.update_text()
        text = "Lorem Ipsum is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industry's standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged. It was popularised in the 1960s with the release of Letraset sheets containing Lorem Ipsum passages, and more recently with desktop publishing software like Aldus PageMaker including versions of Lorem Ipsum."
        
        screen.fill(white)
        self.textbox.draw(text)
        self.attack_button.draw()
        
        # ENEMY GUI
        # Enemy arrow
        screen.blit(self.enemy_mon_name, (20, 10))
        screen.blit(self.lv_text, (200, 10))
        screen.blit(self.lv_enemy_text, (230, 10))
        pygame.draw.rect(screen, black, pygame.Rect(20, 30, 10, 60))
        pygame.draw.rect(screen, black, pygame.Rect(270, 80, 5, 10))
        pygame.draw.rect(screen, black, pygame.Rect(275, 84, 5, 6))
        pygame.draw.rect(screen, black, pygame.Rect(280, 88, 5, 2))
        pygame.draw.rect(screen, black, pygame.Rect(20, 90, 270, 2))

        # enemy bar
        pygame.draw.rect(screen, black, pygame.Rect(45, 35, 40, 15))
        pygame.draw.rect(screen, black, pygame.Rect(45, 50, 215, 2))
        pygame.draw.rect(screen, black, pygame.Rect(250, 35, 10, 15))
        screen.blit(self.hp_text, (50,36))
        screen.blit(self.hp_enemy_text, (45, 55))

        # enemy health bar
        perc = (self.hp_enemy[0]/self.hp_enemy[1])
        health_color = green
        if perc < 0.4 and perc > 0.2:
            health_color = yellow
        elif perc < 0.2:
            health_color = red

        pygame.draw.rect(screen, health_color, pygame.Rect(85, 40, perc*165, 5))

        # enemy mons
        for i in (range(len(self.enemy.team))):
            color = red
            if self.enemy.team[i].fainted:
                color = gray

            pygame.draw.circle(screen, color, (50+(i*20), 80), 5)

        # enemy types
        pygame.draw.rect(screen, col_grass, pygame.Rect(170, 72, 40, 15))
        screen.blit(self.enemy_type1_text, (170, 72))

        pygame.draw.rect(screen, col_poison, pygame.Rect(220, 72, 40, 15))
        screen.blit(self.enemy_type2_text, (220, 72))

        # enemy sprite
        screen.blit(self.enemy_mon_sprite, (320,20))

        # PLAYER GUI
        screen.blit(self.player_mon_name, (255,245))
        screen.blit(self.lv_text, (420, 245))
        screen.blit(self.lv_player_text, (450, 245))

        #Player bar
        pygame.draw.rect(screen, black, pygame.Rect(255, 265, 40, 15))
        pygame.draw.rect(screen, black, pygame.Rect(255, 270, 215, 2))
        pygame.draw.rect(screen, black, pygame.Rect(460, 265, 10, 15))
        pygame.draw.rect(screen, black, pygame.Rect(470, 265, 10, 60))
        screen.blit(self.hp_text, (260,266))
        screen.blit(self.hp_player_text, (255, 285))

        # player health bar
        pygame.draw.rect(screen, green, pygame.Rect(295, 270, 165, 5))
        pygame.draw.rect(screen, black, pygame.Rect(255, 280, 225, 2))

        # Player arrow
        pygame.draw.rect(screen, black, pygame.Rect(230, 325, 250, 2))
        pygame.draw.rect(screen, black, pygame.Rect(235, 323, 5, 2))
        pygame.draw.rect(screen, black, pygame.Rect(240, 319, 5, 6))
        pygame.draw.rect(screen, black, pygame.Rect(245, 315, 5, 10))

        # player mons
        for i in (range(len(self.player.team))):
            color = red
            if self.player.team[i].fainted:
                color = gray

            pygame.draw.circle(screen, color, (350+(i*20), 315), 5)

        screen.blit(self.player_mon_sprite, (30, 220))

        pygame.display.update()
