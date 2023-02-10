import pygame, os
from battle_system import TurnBattleSystem
from player import *

width = 700
height = 600

mon_size = 150
mon_type_size = 15

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

# class that defines the textbox
class TextBox:
    def __init__(self, x, y, text):
        self.x = x
        self.y = y
        self.clicked = False
        self.text = text
        self.font = pygame.font.Font('assets/font/RBYGSC.ttf', 20)

    def blit_text(self, box, text, pos):
        words = [word.split(' ') for word in text.splitlines()]
        space = self.font.size(' ')[0]
        max_width = box.width
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
        self.blit_text(inner, text, (self.x+10, self.y+10))
    
# identifies the move (of the pokemon in battle)
# that the player can use to attack the enemy's one
class MoveButton:
    def __init__(self, x, y, move: Move = None, bs: TurnBattleSystem = None):
        self.x = x
        self.y = y
        self.clicked = False
        self.move = move
        self.name = move.name if move is not None else '-'
        self.font = pygame.font.Font(None, 24)

        self.rendered_name = self.font.render(self.name, True, black)

        if self.move is not None:
            self.type_img = pygame.image.load(os.path.join('assets/sprites/move_types/{type}.png'.format(type = self.move.typing.lower())))
            self.type_img = pygame.transform.scale(self.type_img, (self.type_img.get_width()/1.5, self.type_img.get_height()/1.5))
            self.kind_img = pygame.image.load(os.path.join('assets/sprites/moves/{kind}.png'.format(kind = self.move.physical.lower())))
            self.kind_img = pygame.transform.scale(self.kind_img, (self.kind_img.get_width()/2, self.kind_img.get_height()/2))

        self.bs = bs
        self.player = self.bs.get_player()
        self.enemy = self.bs.get_ai()

        self.player_mon = self.player.in_battle
        self.enemy_mon = self.enemy.in_battle

    def draw(self):
        if self.move is not None:
            rendered_pp = self.font.render('{pp}/{max_pp}'.format(pp = self.move.pp, max_pp = self.move.max_pp), True, black)

        outer = pygame.Rect(self.x, self.y, 125, 100)
        inner = pygame.Rect(self.x+5, self.y+5, 115, 90)
        pygame.draw.rect(screen, black, outer)
        pygame.draw.rect(screen, white, inner)

        screen.blit(self.rendered_name, (self.x+10, self.y+45))

        if self.move is not None:
            screen.blit(rendered_pp, (self.x+75, self.y+75))
            screen.blit(self.kind_img, (self.x+10, self.y+71))
            screen.blit(self.type_img, (self.x+11, self.y+10))

        mouse = pygame.mouse.get_pos()

        if inner.collidepoint(mouse):
            if pygame.mouse.get_pressed()[0] == 1 and self.clicked == False:
                if self.player.is_turn():
                    self.player_mon.try_atk_status(self.move, self.enemy_mon)
                    self.bs.switch_turn()
                else:
                    print('other turn')
                self.clicked = True

        if pygame.mouse.get_pressed()[0] == 0:
            self.clicked = False

# encloses the (max of) four moves of the pokemon in battle
class MoveSelector:
    def __init__(self, bs: TurnBattleSystem = None):
        self.bs = bs
        self.player = self.bs.get_player()        

        self.player_mon = self.player.in_battle

        self.moves = [None] * 4

        for i in range(len(self.moves)):
            self.moves[i] = MoveButton(i*125, 500, self.player_mon.moves[i], self.bs)

    def draw(self):
        for m in self.moves:
            m.draw()

    # updates moves selector when player's pokemon is changed
    def update_player_mon(self, pkmn):
        self.player_mon = pkmn

        for i in range(len(self.moves)):
            self.moves[i] = MoveButton(i*125, 500, self.player_mon.moves[i], self.bs)

    # updates player moves target when enemy's pokemon is changed
    def update_enemy_mon(self):
        self.enemy_mon = self.enemy.in_battle

# button that identifies a pokemon in the player team
# it can be used to change the pokemon in battle
class TeamButton:
    def __init__(self, x, y, pkmn: Pokemon = None, player: Trainer = None):
        self.x = x
        self.y = y
        self.clicked = False
        self.pkmn = pkmn
        self.name = pkmn.name
        self.player = player

        self.font = pygame.font.Font('assets/font/RBYGSC.ttf', 14)

        self.rendered_name = self.font.render(self.name, True, black)
        self.rendered_lv = self.font.render('L. : {level}'.format(level = self.pkmn.level), True, black)

        self.pkmn_img = pygame.image.load(os.path.join('assets/sprites/front/{id}.png'.format(id = self.pkmn.id)))
        self.pkmn_img = pygame.transform.scale(self.pkmn_img, (self.pkmn_img.get_width()/1.25, self.pkmn_img.get_height()/1.25))

        self.pkmn_type1_img = pygame.image.load(os.path.join('assets/sprites/types/{type1}.png'.format(type1 = self.pkmn.typing[0].lower())))
        self.pkmn_type1_img = pygame.transform.scale(self.pkmn_type1_img, (mon_type_size, mon_type_size))
        if len(self.pkmn.typing) == 2:
            self.pkmn_type2_img = pygame.image.load(os.path.join('assets/sprites/types/{type2}.png'.format(type2 = self.pkmn.typing[1].lower())))
            self.pkmn_type2_img = pygame.transform.scale(self.pkmn_type2_img, (mon_type_size, mon_type_size))

    def draw(self):
        outer = pygame.Rect(self.x, self.y, 200, 100)
        inner = pygame.Rect(self.x+5, self.y+5, 190, 90)
        pygame.draw.rect(screen, black, outer)
        pygame.draw.rect(screen, white, inner)

        rendered_hp = self.font.render('{hp}/{max_hp}'.format(hp = int(self.pkmn.hp), max_hp = self.pkmn.max_hp), True, black)
        rendered_status = self.font.render(self.pkmn.status, True, black)

        screen.blit(self.pkmn_img, (self.x+10, self.y+10))
        screen.blit(self.rendered_name, (self.x+65, self.y+10))
        screen.blit(self.rendered_lv, (self.x+10, self.y+75))
        screen.blit(rendered_status, (self.x+100, self.y+75))
        screen.blit(rendered_hp, (self.x+65, self.y+40))

        if len(self.pkmn.typing) == 2:
            screen.blit(self.pkmn_type1_img, (self.x+155, self.y+75))
            screen.blit(self.pkmn_type2_img, (self.x+175, self.y+75))
        else:
            screen.blit(self.pkmn_type1_img, (self.x+175, self.y+75))

        # health bar
        perc = (self.pkmn.hp/self.pkmn.max_hp)
        health_color = green
        if perc < 0.4 and perc > 0.2:
            health_color = yellow
        elif perc < 0.2:
            health_color = red

        pygame.draw.rect(screen, health_color, pygame.Rect(self.x+65, self.y+30, perc*120, 5))

        mouse = pygame.mouse.get_pos()

        if inner.collidepoint(mouse):
            if pygame.mouse.get_pressed()[0] == 1 and self.clicked == False:
                if self.pkmn.fainted != True:
                    self.player.in_battle = self.pkmn         
                else:
                    print('You can\'t use a fainted Pokémon!')   
                self.clicked = True

        if pygame.mouse.get_pressed()[0] == 0:
            self.clicked = False

    # emits a signal if the button is pressed
    # used to trigger the update of the gui
    # when the pokemon is changed
    def emit_signal(self):
        return self.clicked

# class containing six teambuttons
class TeamSelector:
    def __init__(self, player: Trainer = None):
        self.font = pygame.font.Font('assets/font/RBYGSC.ttf', 14)
        self.team = player.team

        self.rendered_text = self.font.render('YOUR TEAM:', True, black)

        self.pkmn = [None] * 6

        for i in range(len(self.pkmn)):
            self.pkmn[i] = TeamButton(500, i*100, self.team[i], player)

    def draw(self):
        for p in self.pkmn:
            p.draw()

    # emits a signal if any of the buttons emits a signal
    def emit_signal(self):
        for p in self.pkmn:
            if p.emit_signal() is True:
                return True
        
class GameWindow:
    def __init__(self, bs: TurnBattleSystem = None, sound=True):
        self.font = pygame.font.Font('assets/font/RBYGSC.ttf', 14)
        self.hp_text = self.font.render('HP :', True, gold)
        self.lv_text = self.font.render('L. :', True, black)

        self.bs = bs

        self.player = self.bs.get_player()
        self.player_mon = self.player.in_battle
        self.player_mon_name = self.font.render(self.player_mon.name, True, black)
        self.player_mon_sprite = pygame.image.load(os.path.join('assets/sprites/back/{id}.png'.format(id = self.player_mon.id)))
        self.player_mon_sprite = pygame.transform.scale(self.player_mon_sprite, (mon_size, mon_size))
        self.hp_player = [self.player_mon.hp, self.player_mon.max_hp]
        self.hp_player_text = self.font.render(str(int(self.hp_player[0])) + '/' + str(self.hp_player[1]), True, black)
        self.lv_player_text = self.font.render(str(self.player_mon.level), True, black)
        self.status_player_text = self.font.render(self.player_mon.status, True, black)
        self.temp_status_player_text = self.font.render(self.player_mon.temp_status, True, black)
        self.player_mon_type1_img = pygame.image.load(os.path.join('assets/sprites/types/{type1}.png'.format(type1 = self.player_mon.typing[0].lower())))
        self.player_mon_type1_img = pygame.transform.scale(self.player_mon_type1_img, (mon_type_size, mon_type_size))
        if len(self.player_mon.typing) == 2:
            self.player_mon_type2_img = pygame.image.load(os.path.join('assets/sprites/types/{type2}.png'.format(type2 = self.player_mon.typing[1].lower())))
            self.player_mon_type2_img = pygame.transform.scale(self.player_mon_type2_img, (mon_type_size, mon_type_size))

        self.enemy = self.bs.get_ai()
        self.enemy_mon = self.enemy.in_battle
        self.enemy_mon_name = self.font.render(self.enemy_mon.name, True, black)
        self.enemy_mon_sprite = pygame.image.load(os.path.join('assets/sprites/front/{id}.png').format(id = self.enemy_mon.id))
        self.enemy_mon_sprite = pygame.transform.scale(self.enemy_mon_sprite, (mon_size, mon_size))
        self.hp_enemy = [self.enemy_mon.hp, self.enemy_mon.max_hp]
        self.hp_enemy_text = self.font.render(str(int(self.hp_enemy[0])) + '/' + str(self.hp_enemy[1]), True, black)
        self.lv_enemy_text = self.font.render(str(self.enemy_mon.level), True, black)
        self.status_enemy_text = self.font.render(self.enemy_mon.status, True, black)
        self.temp_status_enemy_text = self.font.render(self.enemy_mon.temp_status, True, black)
        self.enemy_mon_type1_img = pygame.image.load(os.path.join('assets/sprites/types/{type1}.png'.format(type1 = self.enemy_mon.typing[0].lower())))
        self.enemy_mon_type1_img = pygame.transform.scale(self.enemy_mon_type1_img, (mon_type_size, mon_type_size))
        if len(self.enemy_mon.typing) == 2:
            self.enemy_mon_type2_img = pygame.image.load(os.path.join('assets/sprites/types/{type2}.png'.format(type2 = self.enemy_mon.typing[1].lower())))
            self.enemy_mon_type2_img = pygame.transform.scale(self.enemy_mon_type2_img, (mon_type_size, mon_type_size))

        pygame.mixer.music.load(os.path.join('assets/sounds/battle.mp3'))
        if sound == True:
            pygame.mixer.music.play(-1)

        self.textbox = TextBox(0, 380, 'Prova testo')
     
        self.move_selector = MoveSelector(self.bs)
        self.team_selector = TeamSelector(self.player)

    def update_text(self):
        self.hp_player = [self.player_mon.hp, self.player_mon.max_hp]
        self.hp_player_text = self.font.render(str(int(self.hp_player[0])) + '/' + str(self.hp_player[1]), True, black)
        self.status_player_text = self.font.render(self.player_mon.status, True, black)
        self.temp_status_player_text = self.font.render(self.player_mon.temp_status, True, black)

        self.hp_enemy = [self.enemy_mon.hp, self.enemy_mon.max_hp]
        self.hp_enemy_text = self.font.render(str(int(self.hp_enemy[0])) + '/' + str(self.hp_enemy[1]), True, black)
        self.status_enemy_text = self.font.render(self.enemy_mon.status, True, black)
        self.temp_status_enemy_text = self.font.render(self.enemy_mon.temp_status, True, black)

    def update_player_mon(self):
        self.player_mon = self.player.in_battle
        self.player_mon_name = self.font.render(self.player_mon.name, True, black)
        self.player_mon_sprite = pygame.image.load(os.path.join('assets/sprites/back/{id}.png'.format(id = self.player_mon.id)))
        self.player_mon_sprite = pygame.transform.scale(self.player_mon_sprite, (mon_size, mon_size))
        self.hp_player = [self.player_mon.hp, self.player_mon.max_hp]
        self.hp_player_text = self.font.render(str(self.hp_player[0]) + '/' + str(self.hp_player[1]), True, black)
        self.lv_player_text = self.font.render(str(self.player_mon.level), True, black)
        self.player_mon_type1_img = pygame.image.load(os.path.join('assets/sprites/types/{type1}.png'.format(type1 = self.player_mon.typing[0].lower())))
        self.player_mon_type1_img = pygame.transform.scale(self.player_mon_type1_img, (mon_type_size, mon_type_size))
        if len(self.player_mon.typing) == 2:
            self.player_mon_type2_img = pygame.image.load(os.path.join('assets/sprites/types/{type2}.png'.format(type2 = self.player_mon.typing[1].lower())))
            self.player_mon_type2_img = pygame.transform.scale(self.player_mon_type2_img, (mon_type_size, mon_type_size))
        self.move_selector.update_player_mon(self.player_mon)

    def update_textbox(self, text):
        self.textbox.draw(text)

    def draw(self):
        self.update_text()
        if self.team_selector.emit_signal():
            self.update_player_mon()
        
        screen.fill(white)
        self.textbox.draw(self.player_mon.msg)

        self.move_selector.draw()
        self.team_selector.draw()
        
        # ENEMY GUI
        # Enemy arrow
        screen.blit(self.enemy_mon_name, (20, 10))
        screen.blit(self.lv_text, (185, 10))
        screen.blit(self.lv_enemy_text, (220, 10))
        pygame.draw.rect(screen, black, pygame.Rect(20, 30, 10, 60))
        pygame.draw.rect(screen, black, pygame.Rect(270, 80, 5, 10))
        pygame.draw.rect(screen, black, pygame.Rect(275, 84, 5, 6))
        pygame.draw.rect(screen, black, pygame.Rect(280, 88, 5, 2))
        pygame.draw.rect(screen, black, pygame.Rect(20, 90, 270, 2))

        # enemy bar
        pygame.draw.rect(screen, black, pygame.Rect(45, 35, 40, 15))
        pygame.draw.rect(screen, black, pygame.Rect(45, 50, 215, 2))
        pygame.draw.rect(screen, black, pygame.Rect(250, 35, 10, 15))
        screen.blit(self.hp_text, (47,36))
        screen.blit(self.hp_enemy_text, (45, 55))
        if self.enemy_mon.status != None:
            screen.blit(self.status_enemy_text, (155, 55))
        if self.enemy_mon.temp_status != None:
            screen.blit(self.temp_status_enemy_text, (205, 55))

        # enemy health bar
        perc_en = (self.hp_enemy[0]/self.hp_enemy[1])
        health_en_color = green
        if perc_en < 0.4 and perc_en > 0.2:
            health_en_color = yellow
        elif perc_en < 0.2:
            health_en_color = red

        pygame.draw.rect(screen, health_en_color, pygame.Rect(85, 40, perc_en*165, 5))

        # enemy mons
        for i in (range(len(self.enemy.team))):
            color = red
            if self.enemy.team[i].fainted:
                color = gray

            pygame.draw.circle(screen, color, (50+(i*20), 80), 5)

        # enemy types
        if len(self.enemy_mon.typing) == 2:
            screen.blit(self.enemy_mon_type1_img, (220, 72))
            screen.blit(self.enemy_mon_type2_img, (240, 72))
        else:
            screen.blit(self.enemy_mon_type1_img, (240, 72))

        # enemy sprite
        screen.blit(self.enemy_mon_sprite, (320,20))

        # PLAYER GUI
        screen.blit(self.player_mon_name, (255,245))
        screen.blit(self.lv_text, (405, 245))
        screen.blit(self.lv_player_text, (440, 245))

        #Player bar
        pygame.draw.rect(screen, black, pygame.Rect(255, 265, 40, 15))
        pygame.draw.rect(screen, black, pygame.Rect(460, 265, 10, 15))
        pygame.draw.rect(screen, black, pygame.Rect(470, 265, 10, 60))
        pygame.draw.rect(screen, black, pygame.Rect(255, 280, 225, 2))
        screen.blit(self.hp_text, (257,266))
        screen.blit(self.hp_player_text, (255, 285))
        if self.player_mon.status != None:
            screen.blit(self.status_player_text, (363, 285))
        if self.player_mon.temp_status != None:
            screen.blit(self.temp_status_player_text, (413, 285))

        # player health bar
        perc_pl = (self.hp_player[0]/self.hp_player[1])
        health_pl_color = green
        if perc_pl < 0.4 and perc_pl > 0.2:
            health_pl_color = yellow
        elif perc_pl < 0.2:
            health_pl_color = red

        pygame.draw.rect(screen, health_pl_color, pygame.Rect(295, 270, perc_pl*165, 5))

        # Player arrow
        pygame.draw.rect(screen, black, pygame.Rect(230, 325, 250, 2))
        pygame.draw.rect(screen, black, pygame.Rect(235, 323, 5, 2))
        pygame.draw.rect(screen, black, pygame.Rect(240, 319, 5, 6))
        pygame.draw.rect(screen, black, pygame.Rect(245, 315, 5, 10))

        # enemy types
        screen.blit(self.player_mon_type1_img, (260, 308))
        if len(self.player_mon.typing) == 2:
            screen.blit(self.player_mon_type2_img, (280, 308))

        # player mons
        for i in (range(len(self.player.team))):
            color = red
            if self.player.team[i].fainted:
                color = gray

            pygame.draw.circle(screen, color, (350+(i*20), 315), 5)

        screen.blit(self.player_mon_sprite, (30, 220))

        pygame.display.update()