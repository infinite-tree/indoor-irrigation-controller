import glob
import json
import math
import os
import pygame
from pygame.locals import *
import pytz
import serial
import subprocess
import time

# local imports
import widgets


PRODUCTION = os.getenv("PRODUCTION")
SERIAL_PATTERN = "/dev/ttyUSB*"

UPDATE_DELAY = 5
IDEAL_TEMP = 72.0
TEMP_THRESHOLD = 2.0
TEMP_HOLD = 15/UPDATE_DELAY


def scale(x, in_min, in_max, out_min, out_max):
    return (x-in_min) * (out_max - out_min) / (in_max - in_min) + out_min


class FakeSerial(object):
    def __init__(self, log, *args, **kwargs):
        self.Log = log
        self.Commands = {
            'V': 'or',
            'I': 'I',
            'c': 'c',
            'C': 'C',
            'h': 'h',
            'H': 'H',
            'o': 'o',
            'O': 'O',
            'P': 'P',
            'p': 'p',
            'r': 'r',
            'R': 'R',
            'T': '60.0'
        }
        self.Valves = {
            'c': '',
            'h': '',
            'o': 'o',
            'r': 'r'
        }
        self.Temp = 60.0
        self.Last = ''

    def close(self):
        self.Valves = {
            'c': '',
            'h': '',
            'o': 'o',
            'r': 'r'
        }
        return

    def write(self, value):
        self.Last = value.decode()
        if self.Last.lower() == 'o':
            self.Valves['o'] = self.Last
        elif self.Last.lower() == 'r':
            self.Valves['r'] = self.Last
        elif self.Last == 'c' and len(self.Valves['c']) > 0:
            self.Valves['c'] = self.Valves['c'][:-1]
        elif self.Last == 'C' and len(self.Valves['c']) < 10:
            self.Valves['c'] = self.Valves['c'] + "C"
        elif self.Last == 'h' and len(self.Valves['h']) > 0:
            self.Valves['h'] = self.Valves['h'][:-1]
        elif self.Last == 'H' and len(self.Valves['h']) < 10:
            self.Valves['h'] = self.Valves['h'] + "H"

    def readline(self):
        if self.Last == 'T':
            temp = 75.0 - len(self.Valves['c'])*2 + len(self.Valves['h'])*2
            send = str(temp)
        elif self.Last == 'V':
            send = "".join(self.Valves.values())
        else:
            send = self.Commands.get(self.Last, 'E')
        return (send + "\n").encode()


class Arduino(object):
    def __init__(self, log):
        self.Log = log
        self.Stream = None
        self._newSerial()
        self.Running = False

    def _newSerial(self):
        '''
        Reset the serial device using the DTR lines
        '''
        try:
            self.Stream.close()
        except:
            pass

        if PRODUCTION:
            serial_devices = glob.glob(SERIAL_PATTERN)
            if len(serial_devices) < 1:
                self.Log.error("No Serial devices detected. Restarting ...")
                subprocess.call("sudo reboot", shell=True)

            self.SerialDevice = sorted(serial_devices)[-1]
            self.Stream = serial.Serial(self.SerialDevice, 57600, timeout=1)
        else:
            self.Stream = FakeSerial(self.Log)

        if self._sendData('I') == 'I':
            return
        # still not reset
        self.Log.error("Failed to reset Serial!!!")

    def resetSerial(self):
        try:
            self.Stream.close()
        except:
            pass

        time.sleep(2)
        self._newSerial()

    def _readResponse(self):
        try:
            response = self.Stream.readline().decode('utf-8').strip()
            while len(response) > 0 and response.startswith('D'):
                self.Log.debug(response)
                response = self.Stream.readline().decode('utf-8').strip()
        except Exception as e:
            self.Log.error("Serial exception: %s" % (e), exc_info=1)
            self.resetSerial()

        self.Log.debug("SERIAL - Response: '%s'" % (response))
        return response

    def _sendData(self, value):
        self._readResponse()
        v = bytes(value, 'utf-8')
        self.Log.debug("SERIAL - Sending: %s" % (v))
        self.Stream.write(v)
        return self._readResponse()

    def handleDebugMessages(self):
        self._readResponse()

    def getValveStates(self):
        valves = self._sendData("V")
        state = {
            'cold': valves.count('C')*10,
            'hot': valves.count('H')*10,
            'output': 'CLOSED' if 'o' in valves else 'OPEN',
            'recycle': 'CLOSED' if 'r' in valves else 'OPEN'
        }
        return state

    def getTemperature(self):
        # This should only be called via the WaterMeter class
        try:
            return float(self._sendData("T"))
        except Exception:
            self.Log.error(
                "float conversion failed for Arduino.getTemperature()")
            return 0.0

    def _controlValve(self, value):
        if self._sendData(str(value)) == str(value):
            return True
        return False

    def pulseOpenCold(self):
        return self._controlValve('C')

    def pulseCloseCold(self):
        return self._controlValve('c')

    def pulseOpenHot(self):
        return self._controlValve('H')

    def pulseCloseHot(self):
        return self._controlValve('h')

    def openOutput(self):
        return self._controlValve('O')

    def closeOutput(self):
        return self._controlValve('o')

    def openRecycle(self):
        return self._controlValve('R')

    def closeRecycle(self):
        return self._controlValve('r')

    def startRecyclePump(self):
        return self._controlValve('P')

    def stopRecyclePump(self):
        return self._controlValve('p')


class MixingValveControl(object):
    def __init__(self, pos, size, log, arduino):
        self.Position = pos
        self.Size = size
        self.ValveSize = (121, 64)
        self.Log = log
        self.Arduino = arduino
        self.Font = pygame.font.SysFont("avenir", 48)
        self.Status = widgets.MixingValveStatus((self.Size[0]/2, self.Size[1]/2), self.ValveSize, self.getPercent, center=True) 
        self.Left = widgets.LeftButton((self.Size[0]/2 - self.ValveSize[0],self.Size[1]/2), self.handleLeft, center=True)
        self.Right = widgets.RightButton((self.Size[0]/2 + self.ValveSize[0],self.Size[1]/2), self.handleRight, center=True)

    def getPercent(self):
        return 0

    def handleLeft(self):
        return
    
    def handleRight(self):
        return

    def handleEvent(self, event):
        if hasattr(event, 'pos'):
            event_pos = (event.pos[0] - self.Position[0], event.pos[1] - self.Position[1])
            if event.type == MOUSEBUTTONDOWN:
                if self.Left.handleClick(event_pos):
                    return True
                elif self.Right.handleClick(event_pos):
                    return True
        return False
    
    def render(self, surface):
        base_surface = pygame.surface.Surface(self.Size)
        pygame.draw.rect(base_surface, widgets.WHITE, (0, 0, self.Size[0], self.Size[1]))
        
        text = self.Font.render(self.ValveName, 1, widgets.BLACK)
        txt_size = text.get_size()
        base_surface.blit(text, (self.Size[0]/2 - txt_size[0]/2, 10))

        border = 3
        # top line
        size = (self.ValveSize[0] + border*4, self.ValveSize[1] + border*4)
        tl = (self.Size[0]/2 - self.ValveSize[0]/2 - border*2,
              self.Size[1]/2 - self.ValveSize[1]/2 - border*2)
        pygame.draw.rect(base_surface, widgets.BLACK, [tl[0], tl[1], size[0], border])
        # left line
        pygame.draw.rect(base_surface, widgets.BLACK, [tl[0], tl[1], border, size[1]])
        # bottom line
        pygame.draw.rect(base_surface, widgets.BLACK, [tl[0], tl[1]+size[1]-border, size[0], border])
        # right line
        pygame.draw.rect(base_surface, widgets.BLACK, [tl[0]+size[0]-border, tl[1], border, size[1]])

        self.Status.render(base_surface)

        self.Left.render(base_surface)
        self.Right.render(base_surface)
        surface.blit(base_surface, self.Position)


class ColdControl(MixingValveControl):
    ValveName = ' COLD '
    def getPercent(self):
        return self.Arduino.getValveStates()['cold']
    
    def handleLeft(self):
        self.Arduino.pulseCloseCold()
        self.Status.Percent = self.getPercent()
    
    def handleRight(self):
        self.Arduino.pulseOpenCold()
        self.Status.Percent = self.getPercent()


class HotControl(MixingValveControl):
    ValveName = ' HOT '
    def getPercent(self):
        return self.Arduino.getValveStates()['hot']

    def handleLeft(self):
        self.Arduino.pulseCloseHot()
        self.Status.Percent = self.getPercent()
    
    def handleRight(self):
        self.Arduino.pulseOpenHot()
        self.Status.Percent = self.getPercent()


class OnOffValveControl(object):
    ValveName = "VALVE"
    def __init__(self, pos, size, log, arduino):
        self.Position = pos
        self.Size = size
        self.Log = log
        self.Arduino = arduino
        self.Font = pygame.font.SysFont("avenir", 48)
        self.Button = widgets.OpenCloseButton((self.Size[0]/2, self.Size[1]/2),
                                              self.handleOpen,
                                              self.handleClose,
                                              center=True)
    
    def handleOpen(self):
        return

    def handleClose(self):
        return

    def handleEvent(self, event):
        if hasattr(event, 'pos'):
            event_pos = (event.pos[0] - self.Position[0], event.pos[1] - self.Position[1])
            if event.type == MOUSEBUTTONDOWN:
                if self.Button.handleClick(event_pos):
                    return True
        return False
    
    def render(self, surface):
        base_surface = pygame.surface.Surface(self.Size)
        pygame.draw.rect(base_surface, widgets.WHITE, (0, 0, self.Size[0], self.Size[1]))
        
        text = self.Font.render(self.ValveName, 1, widgets.BLACK)
        txt_size = text.get_size()
        base_surface.blit(text, (self.Size[0]/2 - txt_size[0]/2, 10))

        self.Button.render(base_surface)
        surface.blit(base_surface, self.Position)


class RecirculationControl(OnOffValveControl):
    ValveName = "Recirculation"

    def handleOpen(self):
        self.Log.debug("recirculation open")
        self.Arduino.openRecycle()

    def handleClose(self):
        self.Log.debug("recirculation close")
        self.Arduino.closeRecycle()


class OutputControl(OnOffValveControl):
    ValveName = "Output"

    def handleOpen(self):
        self.Log.debug("output open")
        self.Arduino.openOutput()

    def handleClose(self):
        self.Log.debug("output close")
        self.Arduino.closeOutput()


class TempControl(object):
    def __init__(self, log, arduino, screen):
        self.Log = log
        self.Screen = screen
        self.Size = self.Screen.get_size()
        self.Arduino = arduino

        # Recirculation Pump
        self.Recirculating = False
        self.RecirculationCenter = (345, 282)
        self.RecirculationRadius = 30

        # Output and Recirculation Valve
        self.OutputOpen = False
        self.OutputPosition = (21, 89)
        self.ValveSize = (121, 64)

        self.RecirculationValveOpen = False
        self.RecirculationPosition = (169, 89)

        # Hot and Cold Valves
        self.HotValvePercent = 0
        self.HotValve = widgets.MixingValveStatus((21, 335), self.ValveSize, self.getHotPercent)

        self.ColdValvePercent = 0
        self.ColdValve = widgets.MixingValveStatus((169, 335), self.ValveSize, self.getColdPercent)

        # Temperature
        self.Temperature = 75.0
        self.TemperaturePosition = (155, 245)
        self.TemperatureRadius = 40

        self.Font = pygame.font.SysFont("avenir", 30)
        self.LastUpdate = 0
        self.LastControl = 0
        self.Running = False
        self.updateStatus()
        self.handleStop()

    def getHotPercent(self):
        return self.HotValvePercent

    def getColdPercent(self):
        return self.ColdValvePercent

    def startRecycle(self):
        self.Recirculating = True
        self.Arduino.openRecycle()
        self.Arduino.startRecyclePump()

    def stopRecycle(self):
        self.Recirculating = False
        self.Arduino.stopRecyclePump()
        self.Arduino.closeRecycle()

    def handleStart(self):
        self.Log.info("Starting Temp Controller")
        self.startRecycle()
        for x in range(5):
            self.Arduino.pulseOpenCold()
            self.Arduino.pulseOpenHot()

        self.Running = True
        self.AtTemp = 0
        self.LastControl = time.time()
        self.updateStatus()

    def handleStop(self):
        self.Running = False
        self.AtTemp = 0
        self.Log.info("Stopping Temp Controller")
        self.Arduino.closeOutput()
        self.stopRecycle()
        for x in range(int(self.HotValvePercent/10)):
            self.Arduino.pulseCloseHot()
        for x in range(int(self.ColdValvePercent/10)):
            self.Arduino.pulseCloseCold()

    def handleEvent(self, event):
        # if event.type == MOUSEBUTTONDOWN:
        #     self.ReturnButton.handleClick(event.pos)
        #     return True
        return False

    def updateStatus(self):
        now = time.time()
        if now - self.LastUpdate > 1:
            states = self.Arduino.getValveStates()
            self.HotValvePercent = states['hot']
            self.ColdValvePercent = states['cold']
            self.RecirculationValveOpen = (states['recycle'] == "OPEN")
            self.OutputOpen = (states['output'] == "OPEN")
            self.Temperature = self.Arduino.getTemperature()
            self.LastUpdate = now
        
        # Control logic
        if self.Running and now - self.LastControl > UPDATE_DELAY:
            # Make sure water that is out of temp doesn't go to plants
            if self.Temperature < (IDEAL_TEMP - TEMP_THRESHOLD):
                if self.OutputOpen:
                    self.Log.error("Temp got too cold. cutting water")
                    self.startRecycle()
                    self.Arduino.closeOutput()
                    self.AtTemp = 0
            elif self.Temperature > (IDEAL_TEMP + TEMP_THRESHOLD):
                if self.OutputOpen:
                    self.Log.error("Temp got too hot. cutting water")
                    self.startRecycle()
                    self.Arduino.closeOutput()
                    self.AtTemp = 0
            else:
                # Open the output once it is ready
                self.Log.info("Water is at temp")
                if not self.OutputOpen:
                    self.AtTemp += 1
                    if self.AtTemp >= TEMP_HOLD:
                        self.stopRecycle()
                        self.Arduino.openOutput()

            # Adjust water mixing to maintain even temp
            # TODO: This might lead to huge swings since it will tend to
            #       max out hot and cold first (but we want full pressure/flow)
            if self.Temperature < IDEAL_TEMP:
                if self.HotValvePercent > 100:
                    self.Arduino.pulseOpenHot()
                elif self.ColdValvePercent > 0:
                    self.Arduino.pulseCloseCold()
                else:
                    # Error state
                    self.Log.error("Hot is maxed out")
            elif self.Temperature > IDEAL_TEMP:
                if self.ColdValvePercent < 100:
                    self.Arduino.pulseOpenCold()
                elif self.HotValvePercent > 0:
                    self.Arduino.pulseCloseHot()
                else:
                    # ERROR State
                    self.Log.error("COLD is maxed out")

            self.LastControl = now

    def render(self):
        now = int(time.time())
        self.updateStatus()

        surface = pygame.surface.Surface(self.Size, pygame.SRCALPHA)

        # Recirculation Pump status
        if self.Recirculating:
            if now % 2:
                pygame.draw.circle(surface, widgets.GREEN, self.RecirculationCenter, self.RecirculationRadius, 0)
        else:
            pygame.draw.circle(surface, widgets.RED, self.RecirculationCenter, self.RecirculationRadius, 0)

        # Output Valve Status
        output_rect = (self.OutputPosition[0], self.OutputPosition[1], self.ValveSize[0], self.ValveSize[1])
        if self.OutputOpen:
            if now % 2:
                pygame.draw.rect(surface, widgets.GREEN, output_rect)
        else:
            pygame.draw.rect(surface, widgets.RED, output_rect)

        # Recirculation Valve Status
        recirculation_rect = (self.RecirculationPosition[0], self.RecirculationPosition[1], self.ValveSize[0], self.ValveSize[1])
        if self.RecirculationValveOpen:
            if now % 2:
                pygame.draw.rect(surface, widgets.GREEN, recirculation_rect)
        else:
            pygame.draw.rect(surface, widgets.RED, recirculation_rect)

        # render hot status
        self.HotValve.render(surface)

        # Cold Valve Status
        self.ColdValve.render(surface)

        # Temperature
        pygame.draw.circle(surface, widgets.WHITE, self.TemperaturePosition, self.TemperatureRadius, 0)
        pygame.draw.circle(surface, widgets.BLACK, self.TemperaturePosition, self.TemperatureRadius, 2)
        txt_surface = self.Font.render("%d F"%self.Temperature, 1, widgets.BLACK)
        surface.blit(txt_surface, (self.TemperaturePosition[0]-self.TemperatureRadius/1.5, self.TemperaturePosition[1]-self.TemperatureRadius/2))

        self.Screen.blit(surface, (0,0))


class Settings(object):
    def __init__(self, log, screen, arduino, return_handler):
        self.Log = log
        self.Screen = screen
        self.Size = screen.get_size()
        self.Arduino = arduino
        self.ReturnHandler = return_handler

        # Return button + 4 controls
        widget_size = (self.Size[0]/2, self.Size[1]/2)
        self.ReturnButton = widgets.ReturnButton((self.Size[0]-55, 5), self.handleReturn)
        # Cold: Top Left
        self.ColdControl = ColdControl((0,0), widget_size, self.Log, self.Arduino)
        # Hot: Bottom Left
        self.HotControl = HotControl((0, self.Size[1]/2+1), widget_size, self.Log, self.Arduino)
        # Recirculation: Top Right
        self.RecirculationControl = RecirculationControl((self.Size[0]/2+1,0), widget_size, self.Log, self.Arduino)
        # Output: Bottom Right
        self.OutputControl = OutputControl((self.Size[0]/2+1,self.Size[1]/2+1), widget_size, self.Log, self.Arduino)

    def handleReturn(self):
        self.ReturnHandler()

    def handleEvent(self, event):
        if self.ColdControl.handleEvent(event):
            return True
        if self.HotControl.handleEvent(event):
            return True
        if self.RecirculationControl.handleEvent(event):
            return True
        if self.OutputControl.handleEvent(event):
            return True
        
        if event.type == MOUSEBUTTONDOWN:
            self.ReturnButton.handleClick(event.pos)
        return True
    
    def render(self):
        surface = pygame.surface.Surface(self.Size)
        pygame.draw.rect(surface, widgets.WHITE, (0, 0, self.Size[0], self.Size[1]))
        self.ColdControl.render(surface)
        self.HotControl.render(surface)
        self.RecirculationControl.render(surface)
        self.OutputControl.render(surface)

        self.ReturnButton.render(surface)
        self.Screen.blit(surface, (0,0))

