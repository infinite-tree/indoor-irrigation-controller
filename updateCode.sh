#! /bin/bash


PREV_MD5=`md5sum gui.py`
git fetch origin master
git reset --hard FETCH_HEAD
git clean -df
NEW_MD5=`md5sum gui.py`


echo $PREV_MD5
echo $NEW_MD5

if [ "$PREV_MD5" != "$NEW_MD5" ]; then
    logger -s "Restarting IrrigationService ..."
    sudo systemctl restart irrigation.service
fi
