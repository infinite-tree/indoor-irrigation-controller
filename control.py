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


def scale(x, in_min, in_max, out_min, out_max):
    return (x-in_min) * (out_max - out_min) / (in_max - in_min) + out_min


class FakeSerial(object):
    def __init__(self, log, *args, **kwargs):
        self.Log = log
        self.Buffer = "E"
        return

    def close(self):
        self.Log.debug("FakeSerial.close()")
        return

    def write(self, value):
        self.Buffer = str(value)
        self.Log.debug("FakeSerial.write(%s)"%value)


    def readline(self):
        self.Log.debug("FakeSerial.readline() -> %s"%self.Buffer.strip())
        return (self.Buffer.strip() + "\n").encode()


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

        # FIXME: still needed or delete?
        # FIXME: match device to the actual
        # subprocess.call("sudo ./usbreset /dev/bus/usb/001/002",
        #                 shell=True, cwd=os.path.expanduser("~/"))
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

    def startPump(self):
        return self._controlValve('P')

    def stopPump(self):
        return self._controlValve('p')


class MixingValveControl(object):
    def __init__(self, pos, log, arduino):
        self.Position = pos
        self.Log = log
        self.Arduino = arduino
    
    def handleEvent(self, event):
        return False
    
    def render(self, surface):
        return


class ColdControl(MixingValveControl):
    pass


class HotControl(MixingValveControl):
    pass


class OnOffValveControl(object):
    def __init__(self, pos, log, arduino):
        self.Position = pos
        self.Log = log
        self.Arduino = arduino
    
    def handleEvent(self, event):
        return False
    
    def render(self, surface):
        return


class RecirculationControl(OnOffValveControl):
    pass


class OutputControl(OnOffValveControl):
    pass



# class ManifoldControl(object):
#     def __init__(self, position, log, dmx_connection, upper_channel, lower_channel, update_handler):
#         self.Position = position
#         self.Log = log
#         self.Dmx = dmx_connection
#         self.UpperChannel = upper_channel
#         self.LowerChannel = lower_channel
#         self.UpdateHandler = update_handler

#         self.Background = pygame.image.load(MANIFOLD_BG).convert_alpha()
#         self.Size = self.Background.get_size()
#         self.Font = pygame.font.SysFont("avenir", 36)
#         self.Text = self.Font.render("Manifold", 1, widgets.BLACK)
#         self.TextSize = self.Text.get_size()


#         self.TopLimitY = self.TextSize[1]+20
#         self.BottomLimitY = self.Size[1]-25
#         self.Dragging = False
#         self.SliderOffset = 0

#     def adjustDampers(self, relative_slider_pos):
#         if relative_slider_pos == 50:
#             self.Dmx.setValue(self.UpperChannel, 255)
#             self.Dmx.setValue(self.LowerChannel, 255)
#         elif relative_slider_pos > 50:
#             self.Dmx.setValue(self.UpperChannel, 255)
#             new_pos = 255 - scale(relative_slider_pos, 50, 100, 0, 255)
#             self.Dmx.setValue(self.LowerChannel, new_pos)
#         elif relative_slider_pos < 50:
#             self.Dmx.setValue(self.LowerChannel, 255)
#             new_pos = scale(relative_slider_pos, 0, 50, 0, 255)
#             self.Dmx.setValue(self.UpperChannel, new_pos)

#         self.UpdateHandler()

#     def setSliderPos(self, y_pos):
#         # print("TOP: %d, BOTTOM: %d"%(self.TopLimitY, self.BottomLimitY))
#         rel_y = scale(y_pos, self.TopLimitY, self.BottomLimitY, 0, 100)
#         # invert for slider
#         rel_y = 100 - rel_y
#         self.adjustDampers(rel_y)

#     def getRelativeSliderPos(self):
#         upper = self.Dmx.getValue(self.UpperChannel)
#         lower = self.Dmx.getValue(self.LowerChannel)
#         if upper == 255 and lower == 255:
#             return 50
#         elif upper == 255 and lower < 255:
#             # Slider shold be above the mid point
#             return 100 - scale(lower, 0, 255, 0, 50)
#         elif lower == 255 and upper < 255:
#             # Slider should be below the mid point
#             return scale(upper, 0, 255, 0, 50)
#         else:
#             self.Log.error("Unknown Manifold positions. Lower: %d, Upper: %d"%(lower, upper))
#             return 50

#     def getPhysicalSliderPos(self):
#         y = 100 - self.getRelativeSliderPos()
#         # print("Relative POS: %d"%y)
#         pos = int(scale(y, 0, 100, self.TopLimitY, self.BottomLimitY))
#         # print("Physical POS: %d: %d - %d"%(pos, self.TopLimitY, self.BottomLimitY))
#         return pos

#     def handleEvent(self, event):
#         if hasattr(event, 'pos'):
#             event_pos = (event.pos[0]-self.Position[0], event.pos[1] - self.Position[1])

#         if event.type == MOUSEBUTTONDOWN:
#             if self.Dot.collidepoint(event_pos):
#                 self.Dragging = True
#                 self.SliderOffset = self.Dot.y - event_pos[1]
#                 # print("SLIDER OFFSET: %d"%self.SliderOffset)
#                 return True
#         if event.type == MOUSEBUTTONUP:
#             self.Dragging = False
#             return True
#         if event.type == MOUSEMOTION and self.Dragging:
#             new_pos = min(self.BottomLimitY, event_pos[1] + self.SliderOffset)
#             new_pos = max(self.TopLimitY, new_pos)
#             self.setSliderPos(new_pos)
#             return True
#         return False

#     def render(self, surface):
#         base_surface = pygame.surface.Surface(self.Size, pygame.SRCALPHA)
#         base_surface.blit(self.Background, (0,0))

#         base_surface.blit(self.Text, (self.Size[0]/2 - self.TextSize[0]/2, 10))
#         mid = (self.BottomLimitY - self.TopLimitY)/2 + self.TopLimitY
#         pygame.draw.line(base_surface,
#                          widgets.BLACK,
#                          (self.Size[0]-30, self.TopLimitY),
#                          (self.Size[0]-30, self.BottomLimitY),
#                          2)
#         pygame.draw.line(base_surface,
#                          widgets.BLACK,
#                          (self.Size[0]-30-25, self.TopLimitY),
#                          (self.Size[0]-5, self.TopLimitY),
#                          2)
#         pygame.draw.line(base_surface,
#                          widgets.BLACK,
#                          (self.Size[0]-30-25, mid),
#                          (self.Size[0]-5, mid),
#                          1)
#         pygame.draw.line(base_surface,
#                          widgets.BLACK,
#                          (self.Size[0]-30-25, self.BottomLimitY),
#                          (self.Size[0]-5, self.BottomLimitY),
#                          2)

#         # Draw Position
#         y_pos = self.getPhysicalSliderPos()
#         self.Dot = pygame.draw.circle(base_surface,
#                                       widgets.BLACK,
#                                       (self.Size[0]-30, y_pos),
#                                       20)

#         surface.blit(base_surface, self.Position)
#         return


# class BlowerControl(object):
#     def __init__(self, position, log, dmx_connection, channel, update_handler):
#         self.Position = position
#         self.Log = log
#         self.Dmx = dmx_connection
#         self.Channel = channel
#         self.UpdateHandler = update_handler

#         self.Background = pygame.image.load(BLOWER_BG).convert_alpha()
#         self.Size = self.Background.get_size()
#         self.Font = pygame.font.SysFont("avenir", 36)
#         self.Text = self.Font.render("Blower", 1, widgets.BLACK)
#         self.TextSize = self.Text.get_size()

#         self.LineEnd = (self.Size[0]-180, self.Size[1]-20)
#         self.ControlRadius = 115
#         self.AngleLimit = (3.6, 4.9)
#         self.BlowerLimit = (0, 255)

#         self.UpButton = widgets.UpButton((self.Size[0]-55, 60), self.handleUp)
#         self.DownButton = widgets.DownButton((self.Size[0]-55, self.Size[1]-60), self.handleDown)
#         self.Increment = 13

#     def getControlPoint(self):
#         value = float(self.Dmx.getValue(self.Channel))
#         # scale 0-255 to degrees in radians
#         angle = scale(value, 0.0, 255.0, self.AngleLimit[0], self.AngleLimit[1])
#         x = self.LineEnd[0] + (self.ControlRadius * math.cos(angle))
#         y = self.LineEnd[1] + (self.ControlRadius * math.sin(angle))
#         return (int(x),int(y))

#     def handleUp(self):
#         v = self.Dmx.getValue(self.Channel)
#         v = min(self.BlowerLimit[1], v+self.Increment)
#         self.Dmx.setValue(self.Channel, v)
#         self.UpdateHandler()

#     def handleDown(self):
#         v = self.Dmx.getValue(self.Channel)
#         v = max(self.BlowerLimit[0], v-self.Increment)
#         self.Dmx.setValue(self.Channel, v)
#         self.UpdateHandler()

#     def handleEvent(self, event):
#         if hasattr(event, 'pos'):
#             event_pos = (event.pos[0]-self.Position[0],
#                          event.pos[1] - self.Position[1])

#         if event.type == MOUSEBUTTONDOWN:
#             if self.UpButton.handleClick(event_pos):
#                 return True
#             if self.DownButton.handleClick(event_pos):
#                 return True
#         return False

#     def render(self, surface):
#         base_surface = pygame.surface.Surface(self.Size, pygame.SRCALPHA)
#         base_surface.blit(self.Background, (0,0))

#         base_surface.blit(self.Text, (self.Size[0]/2 - self.TextSize[0]/2, 10))
#         zero = self.Font.render("0", 1, widgets.BLACK)
#         hundred = self.Font.render("100", 1, widgets.BLACK)
#         base_surface.blit(zero, (self.Size[0]/2 - 90, self.Size[1]-zero.get_size()[1]))
#         base_surface.blit(hundred, (self.Size[0]-125, 100))

#         # draw buttons
#         self.UpButton.render(base_surface)
#         self.DownButton.render(base_surface)

#         # draw line control
#         pos = self.getControlPoint()
#         pygame.draw.line(base_surface,
#                          widgets.BLACK,
#                          self.LineEnd,
#                          pos,
#                          8)
#         pygame.draw.circle(base_surface,
#                            widgets.BLACK,
#                            pos,
#                            25)

#         surface.blit(base_surface, self.Position)
#         return


# class RecirculationControl(object):
#     def __init__(self, position, log, dmx_connection, channel, update_handler):
#         self.Position = position
#         self.Log = log
#         self.Dmx = dmx_connection
#         self.Channel = channel
#         self.UpdateHandler = update_handler

#         self.Size = (400,240)
#         self.Font = pygame.font.SysFont("avenir", 36)
#         self.Text = self.Font.render("Recirculation", 1, widgets.BLACK)
#         self.TextSize = self.Text.get_size()

#         self.LineEnd = (self.Size[0]-180, self.Size[1]-20)
#         self.ControlRadius = 115
#         self.AngleLimit = (3.6, 4.9)
#         self.BlowerLimit = (0, 255)

#         self.UpButton = widgets.UpButton((self.Size[0]-55, 60), self.handleUp)
#         self.DownButton = widgets.DownButton((self.Size[0]-55, self.Size[1]-60), self.handleDown)
#         self.Increment = 13

#     def handleUp(self):
#         v = self.Dmx.getValue(self.Channel)
#         v = min(self.BlowerLimit[1], v+self.Increment)
#         self.Dmx.setValue(self.Channel, v)
#         self.UpdateHandler()

#     def handleDown(self):
#         v = self.Dmx.getValue(self.Channel)
#         v = max(self.BlowerLimit[0], v-self.Increment)
#         self.Dmx.setValue(self.Channel, v)
#         self.UpdateHandler()

#     def handleEvent(self, event):
#         if hasattr(event, 'pos'):
#             event_pos = (event.pos[0]-self.Position[0],
#                          event.pos[1] - self.Position[1])

#         if event.type == MOUSEBUTTONDOWN:
#             if self.UpButton.handleClick(event_pos):
#                 return True
#             if self.DownButton.handleClick(event_pos):
#                 return True
#         return False

#     def renderWedge(self, surface, center, radius, start_angle, stop_angle):
#         p = [(center[0], center[1])]
#         for n in range(start_angle, stop_angle):
#             x = center[0] + int(radius*math.cos(n*math.pi/180))
#             y = center[1]+int(radius*math.sin(n*math.pi/180))
#             p.append((x, y))
#         p.append((center[0], center[1]))

#         # Draw pie segment
#         if len(p) > 2:
#             pygame.draw.polygon(surface, (0, 0, 0), p)

#     def render(self, surface):
#         base_surface = pygame.surface.Surface(self.Size)
#         pygame.draw.rect(base_surface, widgets.WHITE,
#                          (0, 0, self.Size[0], self.Size[1]))

#         base_surface.blit(self.Text, (self.Size[0]/2 - self.TextSize[0]/2, 10))

#         center = (int(self.Size[0]/2), int(self.Size[1]/2)+20)
#         radius = 75
#         pygame.draw.circle(base_surface, widgets.BLACK, center, radius, 2)

#         v = self.Dmx.getValue(self.Channel)
#         angle = int(scale(255-v, 0, 255, 0, 180))

#         # draw buttons
#         self.UpButton.render(base_surface)
#         self.DownButton.render(base_surface)

#         # draw line control
#         self.renderWedge(base_surface, center, radius, 0, angle)
#         self.renderWedge(base_surface, center, radius, 180, 180+angle)

#         surface.blit(base_surface, self.Position)
#         return


class TempControl(object):
    def __init__(self, log, arduino, screen):
        self.Log = log
        self.Screen = screen
        self.Size = self.Screen.get_size()
        self.Arduino = arduino

        # Recirculation Pump
        self.Recirculating = False
        self.RecirculationCenter = (345, 281)
        self.RecirculationRadius = 30

        # Output and Recirculation Valve
        self.OutputOpen = False
        self.OutputPosition = (21, 89)
        self.ValveSize = (121, 64)

        self.RecirculationValveOpen = False
        self.RecirculationPosition = (169, 89)

        # Hot and Cold Valves
        self.HotValvePercent = 0
        self.HotValvePosition = (21, 335)

        self.ColdValvePercent = 0
        self.ColdValvePosition = (169, 335)

        # Temperature
        self.Temperature = 75.0
        self.TemperaturePosition = (155, 245)
        self.TemperatureRadius = 40

        self.Font = pygame.font.SysFont("avenir", 30)
        self.LastUpdate = time.time()
        self.Running = False
        self.handleStop()


    def handleStart(self):
        self.Running = True
        self.Log.info("Starting Temp Controller")
        # HACK/FIXME
        self.LastUpdate = time.time()

    def handleStop(self):
        self.Running = False
        self.Log.info("Stopping Temp Controller")
        # HACK/FIXME

    def handleEvent(self, event):
        if event.type == MOUSEBUTTONDOWN:
            # self.ReturnButton.handleClick(event.pos)
            return True
        return False

    def updateStatus(self):
        # FIXME: implement
        return

    def render(self):
        now = int(time.time())
        if now % 2:
            self.updateStatus()

        surface = pygame.surface.Surface(self.Size, pygame.SRCALPHA)

        # Recirculation Pump status
        if self.Recirculating:
            if now % 2:
                pygame.draw.circle(surface, widgets.GREEN, self.RecirculationCenter, self.RecirculationRadius, 0)

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

        # Hot Valve Status
        if self.HotValvePercent > 0:
            hot_width = int(self.ValveSize[0] * (self.HotValvePercent/100))
            hot_rect = (self.HotValvePosition[0], self.HotValvePosition[1], hot_width, self.ValveSize[1])
            pygame.draw.rect(surface, widgets.GREEN, hot_rect)
        else:
            hot_rect = (self.HotValvePosition[0], self.HotValvePosition[1], self.ValveSize[0], self.ValveSize[1])
            pygame.draw.rect(surface, widgets.RED, hot_rect)

        # Cold Valve Status
        if self.ColdValvePercent > 0:
            cold_width = int(self.ValveSize[0] * (self.ColdValvePercent/100))
            cold_rect = (self.ColdValvePosition[0], self.ColdValvePosition[1], cold_width, self.ValveSize[1])
            pygame.draw.rect(surface, widgets.GREEN, cold_rect)
        else:
            cold_rect = (self.ColdValvePosition[0], self.ColdValvePosition[1], self.ValveSize[0], self.ValveSize[1])
            pygame.draw.rect(surface, widgets.RED, cold_rect)

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

        self.ReturnButton = widgets.ReturnButton((self.Size[0]-55, 5), self.handleReturn)
        self.ColdControl = ColdControl((0,0), self.Log, self.Arduino)
        self.HotControl = HotControl((0, self.Size[1]/2+1), self.Log, self.Arduino)
        self.RecirculationControl = RecirculationControl((self.Size[0]/2+1,0), self.Log, self.Arduino)
        self.OutputControl = OutputControl((self.Size[0]/2+1,self.Size[1]/2+1), self.Log, self.Arduino)

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
        self.ReturnButton.render(surface)
        self.ColdControl.render(surface)
        self.HotControl.render(surface)
        self.RecirculationControl.render(surface)
        self.OutputControl.render(surface)

        self.Screen.blit(surface, (0,0))

