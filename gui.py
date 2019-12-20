#! /usr/bin/env python3

import pygame
from pygame.locals import *
import logging
import logging.handlers
import os
import subprocess
import sys
import time
import threading


# Local imports
import control
import data
import widgets

PRODUCTION = os.getenv("PRODUCTION")
SCREEN_SIZE=(800,480)

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "img")
BACKGROUND_IMAGE = os.path.join(IMG_DIR, "main-background.png")
LOG_FILE = "~/logs/irrigation-controller.log"

SLEEP_DELAY = 15*60
SCREEN_ON = os.path.join(BASE_DIR, "screen-on.sh")
SCREEN_OFF = os.path.join(BASE_DIR, "screen-off.sh")

DATA_INTERVAL = 1*60


class App(object):
    def __init__(self, log):
        self.Log = log

        self.DataSource = data.DataSource(self.Log)
        # self.Temp = self.DataSource.queryCurrentTemps()
        self.Temp = {}
        self.Humidity = {}
        self.InSettings = False
        self.DataThread = threading.Thread(target=self.dataDaemon, args=(DATA_INTERVAL,), daemon=True)
        self.DataThread.start()

        self.Sleeping = False
        self.LastMovement = time.time()

        if PRODUCTION:
            # Work around for bug in libsdl
            os.environ['SDL_VIDEO_WINDOW_POS'] = "{0},{1}".format(0, 0)
            pygame.init()
            self.Screen = pygame.display.set_mode((0, 0), pygame.NOFRAME)
            pygame.mouse.set_visible(False)

            # self.Screen = pygame.display.set_mode((0, 0), FULLSCREEN)
            # pygame.mouse.set_visible(0)
        else:
            pygame.init()
            self.Screen = pygame.display.set_mode(SCREEN_SIZE)

        self.Clock = pygame.time.Clock()

        self.Background = pygame.image.load(BACKGROUND_IMAGE)
        self.PowerButton = widgets.PowerButton((SCREEN_SIZE[0]-55, 5), self.handlePower)
        self.SettingsButton = widgets.SettingsButton((SCREEN_SIZE[0] - (55*2),5), self.handleSettings)
        self.Font = pygame.font.SysFont("avenir", 18)

        self.Arduino = control.Arduino(self.Log)
        self.TempController = control.TempControl(self.Log, self.Arduino, self.Screen)
        self.Settings = control.Settings(self.Log, self.Screen, self.Arduino, self.handleSettings)

        #
        # Sensor Widgets
        #

        self.TimerControl = widgets.TimerControl((250,5),
                                                 self.TempController.handleStart,
                                                 self.TempController.handleStop)
        # Position will get updated on first render
        self.StartStop = widgets.StartStopButton((250,5), self.TimerControl.start, self.TimerControl.stop)


    def dataDaemon(self, interval):
        while True:
            try:
                # self.Temp = self.DataSource.queryCurrentTemps()
                # self.Humidity = self.DataSource.queryCurrentHumidty()
                # self.Log.debug("DataDaemon: %s, %s"%(self.Temp, self.Humidity))
                time.sleep(interval)
            except Exception as e:
                self.Log.error("Daemon error: %s"%str(e))

    def handlePower(self):
        if self.Sleeping:
            self.wakeUp()
        else:
            self.sleep()
            time.sleep(0.5)

    def wakeUp(self):
        self.Log.info("Wakeup!")
        self.Sleeping = False
        if PRODUCTION:
            subprocess.run(SCREEN_ON, shell=True)

    def sleep(self):
        self.Log.info("Sleeping")
        self.Sleeping = True
        if PRODUCTION:
            subprocess.run(SCREEN_OFF, shell=False)

    def handleSettings(self):
        # Toggle settings mode
        self.InSettings = not self.InSettings

    def handleEvents(self):
        now = time.time()
        for event in pygame.event.get():
            if self.Sleeping:
                self.LastMovement = now
                self.wakeUp()
                pygame.event.clear()
                return True

            # self.Log.debug("Event: %d,%d"%event.pos)
            # self.Log.debug("Mouse: %d,%d"%pygame.mouse.get_pos())

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    pygame.event.clear()
                    return False

            if event.type == QUIT:
                return False

            if self.InSettings:
                # self.Log.debug("In settings")
                self.Settings.handleEvent(event)
            else:
                if event.type == MOUSEBUTTONDOWN:
                    self.LastMovement = now
                    # self.Log.debug("Event pos: %d,%d"%(event.pos))
                    # self.Log.debug("Start Rect: %s"%(self.StartStop.Rectangle))
                    self.PowerButton.handleClick(event.pos)
                    self.SettingsButton.handleClick(event.pos)
                    self.StartStop.handleClick(event.pos)
                    self.TempController.handleEvent(event)

            pygame.event.clear()

        if now - self.LastMovement > SLEEP_DELAY and not self.Sleeping:
            self.sleep()

        return True

    def run(self):
        while True:
            self.Clock.tick(30)
            if not self.handleEvents():
                return


            if self.InSettings:
                # self.Log.debug("FIXME: Settings")
                self.Settings.render()
            else:
                self.Screen.blit(self.Background, (0,0))
                self.PowerButton.render(self.Screen)
                self.SettingsButton.render(self.Screen)
                self.TimerControl.render(self.Screen)
                self.StartStop.Position = (250+self.TimerControl.Rectangle.size[0], 5)
                self.StartStop.render(self.Screen)
                self.TempController.render()

            pygame.display.flip()



if __name__ == "__main__":
    log = logging.getLogger('DryerGUILogger')
    if PRODUCTION:
        log.setLevel(logging.INFO)
    # else:
    #     log.setLevel(logging.DEBUG)
    log.setLevel(logging.DEBUG)
    log_file = os.path.realpath(os.path.expanduser(LOG_FILE))
    # FIXME: TimedFileHandler
    handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=500000, backupCount=5)

    log.addHandler(handler)
    log.addHandler(logging.StreamHandler())
    log.info("Dryer GUI Starting...")

    try:
        app = App(log)
        app.run()
    except Exception as e:
        log.error("Main loop failed: %s"%(e), exc_info=1)
        sys.exit(1)
