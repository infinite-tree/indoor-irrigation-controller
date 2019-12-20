# Indoor Irrigation Controller 
Display and control system for indoor irrigation controller

## Hardware
Raspberry Pi with 7" touchscreen + arduino nano


## Installation Notes

```
sudo cp xorg_irrigation_controller.sh /etc/X11/Xsession.d/91irrigation_controller
sudo chmod +x /etc/X11/Xsession.d/91irrigation_controller
```


## Uploading to the Arduino

**Checkout pio remote agent**

Or on the rpi
```
pio run -t upload
```