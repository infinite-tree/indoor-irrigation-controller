import pygame
from pygame.locals import *
import os
import time

IMG_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "img")
POWER_BTN = os.path.join(IMG_DIR, "power-btn.png")
RETURN_BTN = os.path.join(IMG_DIR, "return.png")
SETTINGS_BTN = os.path.join(IMG_DIR, "settings.png")
TEMP_BADGE = os.path.join(IMG_DIR, "temp-badge.png")
UP_BTN = os.path.join(IMG_DIR, "up.png")
DOWN_BTN = os.path.join(IMG_DIR, "down.png")
LEFT_BTN = os.path.join(IMG_DIR, "left.png")
RIGHT_BTN = os.path.join(IMG_DIR, "right.png")


WHITE = (255, 255, 255)
GREY = (200, 200, 200)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)


class ImageButton(object):
    ImageFile = None
    def __init__(self, position, handler, center=False):
        self.Image = pygame.image.load(self.ImageFile)
        if center:
            s = self.Image.get_size()
            self.Position = (position[0] - s[0]/2, position[1] - s[1]/2)
        else:
            self.Position = position
        self.Rect = self.Image.get_rect().move(self.Position)
        self.Handler = handler

    def render(self, surface, pos=None):
        if pos:
            self.Position = pos
            self.Rect = self.Rect.move(pos)

        surface.blit(self.Image, self.Position)

    def handleClick(self, event_pos):
        # print("Rect: %s, pos: %s"%(self.Rect, event_pos))
        if self.Rect.collidepoint(event_pos):
            self.callback()
            return True
        return False

    def callback(self):
        self.Handler()


class PowerButton(ImageButton):
    ImageFile = POWER_BTN


class ReturnButton(ImageButton):
    ImageFile = RETURN_BTN

class SettingsButton(ImageButton):
    ImageFile = SETTINGS_BTN


class UpButton(ImageButton):
    ImageFile = UP_BTN


class DownButton(ImageButton):
    ImageFile = DOWN_BTN


class LeftButton(ImageButton):
    ImageFile = LEFT_BTN


class RightButton(ImageButton):
    ImageFile = RIGHT_BTN


# class TempAndHumidity(object):
#     def __init__(self, position, data_func, data_args):
#         self.Position = position
#         self.DataFunc = data_func
#         self.DataArgs = data_args

#         self.Image = pygame.image.load(TEMP_BADGE).convert_alpha()
#         # self.Image.set_colorkey((0, 0, 0))
#         # pygame.Surface.convert_alpha(self.Image)
#         self.Font = pygame.font.SysFont("avenir", 20)
#         self.updateValues()

#     def updateValues(self):
#         if self.DataFunc:
#             self.Temp, self.Humidity = self.DataFunc(*self.DataArgs)
#         else:
#             # temp = "%d F"%(t)
#             # humidity = "%d %"%(h)
#             self.Temp = "76 F"
#             self.Humidity = "66 %"

#     def render(self, surface):
#         self.updateValues()
#         size = self.Image.get_rect().size
#         badge_surface = pygame.surface.Surface(size, pygame.SRCALPHA)
#         badge_surface.blit(self.Image, (0,0))


#         temp_surface = self.Font.render(self.Temp, 1, BLACK)
#         humidity_surface = self.Font.render(self.Humidity, 1, BLACK)
#         # TODO: don't hard code the positions
#         badge_surface.blit(temp_surface, (11, 7))
#         badge_surface.blit(humidity_surface, (10, 26))

#         surface.blit(badge_surface, self.Position)


class StartStopButton(object):
    StartText = " START "
    StopText = " STOP "
    def __init__(self, position, start_callback, stop_callback, center=False):
        self.Position = position
        self.On = False
        self.StartCallback = start_callback
        self.StopCallback = stop_callback
        self.Font = pygame.font.SysFont("avenir", 48)
        self.Rectangle = pygame.Rect((0,0,0,0))
        self.Center = center

    def render(self, surface):
        if self.On:
            text = self.Font.render(self.StopText, 1, BLACK)
        else:
            text = self.Font.render(self.StartText, 1, BLACK)

        size = text.get_rect().size
        base_surface = pygame.surface.Surface(size, pygame.SRCALPHA)
        base_surface.blit(text, (0,0))
        border = 2
        # top line
        pygame.draw.rect(base_surface, BLACK, [0, 0, size[0], border])
        # left line
        pygame.draw.rect(base_surface, BLACK, [0, 0, border, size[1]])
        # bottom line
        pygame.draw.rect(base_surface, BLACK, [0, size[1]-border, size[0], size[1]])
        # right line
        pygame.draw.rect(base_surface, BLACK, [size[0]-border, 0, size[0], size[1]])

        if self.Center:
            rect = (self.Position[0] - size[0]/2,
                    self.Position[1] - size[1]/2,
                    size[0],
                    size[1])
        else:
            rect = (self.Position[0], self.Position[1], size[0], size[1])
        surface.blit(base_surface, (rect[0], rect[1]))
        self.Rectangle = pygame.Rect(*rect)

    def handleClick(self, event_pos):
        # print("Rect: %s, pos: %s"%(self.Rectangle, event_pos))
        if self.Rectangle.collidepoint(event_pos):
            if self.On:
                self.On = False
                self.StopCallback()
            else:
                self.On = True
                self.StartCallback()


class OpenCloseButton(StartStopButton):
    StartText = " OPEN "
    StopText = " CLOSE "


class TimerControl(object):
    def __init__(self, position, start_handler, stop_handler):
        self.Position = position
        self.StartHandler = start_handler
        self.StopHandler = stop_handler
        self.StartTime = None
        self.Running = False
        self.Font = pygame.font.SysFont("avenir", 48)

    def start(self):
        self.StartTime = time.time()
        self.Running = True
        self.StartHandler()

    def stop(self):
        self.StartTime = None
        self.Running = False
        self.StopHandler()

    def render(self, surface):
        if self.Running:
            elapsed = time.time() - self.StartTime
        else:
            elapsed = 0

        m, seconds = divmod(elapsed, 60)
        hours, minutes = divmod(m, 60)
        text = self.Font.render(" %02d:%02d:%02d "%(hours, minutes, seconds), 1, BLACK)
        size = text.get_rect().size
        base_surface = pygame.surface.Surface(size, pygame.SRCALPHA)
        base_surface.blit(text, (0,0))
        border = 2
        # top line
        pygame.draw.rect(base_surface, BLACK, [0, 0, size[0], border])
        # left line
        pygame.draw.rect(base_surface, BLACK, [0, 0, border, size[1]])
        # bottom line
        pygame.draw.rect(base_surface, BLACK, [0, size[1]-border, size[0], size[1]])
        # right line
        pygame.draw.rect(base_surface, BLACK, [size[0]-border, 0, size[0], size[1]])

        surface.blit(base_surface, self.Position)
        self.Rectangle = base_surface.get_rect()


class MixingValveStatus(object):
    def __init__(self, position, size, valve_percent_handler, center=False):
        if center:
            self.Position = (position[0] - size[0]/2, position[1] - size[1]/2)
        else:
            self.Position = position
        self.Size = size
        self.GetValvePercent = valve_percent_handler
        self.Center = center
        self.LastTime = time.time()
        self.Percent = 0

    def render(self, surface):
        # Valve Status
        now = time.time()
        if now - self.LastTime > 3:
            self.Percent = self.GetValvePercent()
            self.LastTime = now

        if self.Percent > 0:
            width = int(self.Size[0] * (self.Percent/100))
            rect = (self.Position[0], self.Position[1], width, self.Size[1])
            pygame.draw.rect(surface, GREEN, rect)
        else:
            rect = (self.Position[0], self.Position[1], self.Size[0], self.Size[1])
            pygame.draw.rect(surface, RED, rect)

