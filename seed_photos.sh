#!/bin/sh
rm -rf /home/pi/photos_seed/*
cp /home/pi/photos/* /home/pi/photos_seed/
chown -R pi /home/pi/photos_seed
chgrp -R pi /home/pi/photos_seed
