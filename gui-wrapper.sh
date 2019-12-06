#! /bin/sh

export PRODUCTION=1
logger "Starting Irrigation Controller"
while [ 1 ] ; do
    python3 /home/pi/indoor-irrigation-controller/gui.py 2>&1 | logger
    sleep 5
    logger "Restarting Irrigation Controller"
done
