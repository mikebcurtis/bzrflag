import pygame
from pygame.locals import *

from code import InteractiveConsole as IC
import string
import sys
import collide
import paths


class Console(object):
    def __init__(self, game, rect):
        self.rect = pygame.Rect(rect)
        self.minrect = pygame.Rect(self.rect.bottom-30,self.rect.right-30,30,30)
        self.image = pygame.Surface(self.rect.size)
        self.dirty = True
        self.txt = ''
        self.game = game
        self.at = 0
        self.font = pygame.font.Font(paths.FONT_FILE,16)
        self.lineheight = 15
        self.maxlines = 14
        self.minimized = True
        self.bgc = (0,110,7)

    def write(self, text):
        self.txt = self.txt[:self.at] + text + self.txt[self.at:]
        self.at += len(text)
        self.dirty = True

    def render(self):
        if not self.dirty:return
        self.image.fill(self.bgc)#006E0700))
        lnx = len('\n'.join(self.txt.split('\n')[:-self.maxlines]))
        if lnx>0:lnx+=1
        wpos = False
        for i,line in enumerate(self.txt.split('\n')[-self.maxlines:]):
            self.image.blit(self.font.render(line,1,(0,0,0),self.bgc),(10,self.lineheight*i+10))
            if not wpos and lnx + len(line)>=self.at:
                wpos = True
                pygame.draw.rect(self.image,(0,0,0),(10 + self.font.size(line[:self.at-lnx])[0],self.lineheight*i+10,2,self.lineheight))
            lnx += len(line) + 1

        nrect = pygame.Rect(self.minrect)
        nrect.bottomright = self.rect.size
        pygame.draw.rect(self.image, (255,255,255), nrect)
        pygame.draw.rect(self.image, self.bgc, nrect.inflate(-6,-6))
        self.dirty = False

    def draw(self, screen):
        if self.minimized:
            pygame.draw.rect(screen, (255,255,255), self.minrect)
            pygame.draw.rect(screen, self.bgc, self.minrect.inflate(-6,-6))
        else:
            self.render()
            screen.blit(self.image, self.rect)
    
    def event(self, e):
        if e.type == MOUSEBUTTONDOWN:
            if self.minrect.collidepoint(e.pos):
                self.minimized = not self.minimized
                if self.minimized:
                    self.game.display.redraw()
                return True

class TelnetConsole(Console):
    def __init__(self, *a, **b):
        super(TelnetConsole, self).__init__(*a, **b)
        self.frozen = False
    def render(self):
        if self.frozen:return
        super(TelnetConsole, self).render()
    def event(self, e):
        if super(TelnetConsole, self).event(e):
            return
        elif e.type == KEYDOWN and e.key == K_SPACE:
            self.frozen = not self.frozen


class PyConsole(Console):
    def __init__(self, game, rect):
        super(PyConsole, self).__init__(game, rect)
        self.console = IC({'game':game,'sys':sys,'pygame':pygame,'self':self,'purple':game.map.teams['purple'],'collide':collide})
        self.history = []
        self.athistory = 0
        self.prompt()

    def prompt(self):
        self.txt += '>>> '
        self.index = len(self.txt)
        self.at = self.index

    def execute(self):
        next = self.txt[self.index:]
        self.athistory = len(self.history)+1
        if not (len(self.history) and next == self.history[-1]):
            self.history.append(next)
        self.txt += '\n'
        self.at = len(self.txt)
        sys.stderr = self
        sys.stdout = self
        self.console.push(next+'\n')
        sys.stderr = sys.__stderr__
        sys.stdout = sys.__stdout__
        self.prompt()

    def rehistory(self):
        if 0 <= self.athistory < len(self.history):
            self.txt = self.txt[:self.index] + self.history[self.athistory]
            self.at = len(self.txt)
        else:
            if self.athistory < -1:
                self.athistory = -1
            if self.athistory > len(self.history):
                self.athistory = len(self.history)
            self.txt = self.txt[:self.index]
            self.at = len(self.txt)

    def event(self, e):
        if super(PyConsole, self).event(e):
            return
        elif e.type == KEYDOWN:
            if self.minimized:return
            if e.key == 8:
                if self.at>self.index:
                    self.txt = self.txt[:self.at-1] + self.txt[self.at:]
                    self.at -= 1
                    if self.at < self.index:
                        self.at = self.index
            elif e.key == 13:
                self.execute()
            elif e.key == K_UP:
                self.athistory -= 1
                self.rehistory()
            elif e.key == K_DOWN:
                self.athistory += 1
                self.rehistory()
            elif e.key == K_LEFT:
                if self.at>self.index:self.at-=1
            elif e.key == K_RIGHT:
                if self.at<len(self.txt):
                    self.at+=1
            elif e.unicode in string.printable:
                self.write(e.unicode)
            else:return
            self.dirty = True
