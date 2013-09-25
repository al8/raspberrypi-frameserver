#!/bin/bash
if [ ! -d /tmp/photos ]; then
  mkdir /tmp/photos
fi;
if [ ! -d /home/pi/photos ]; then
  ln -s /tmp/photos /home/pi/photos
fi;
if [ -z "$(ls -A /home/pi/photos)" ]; then
  cp /home/pi/photos_seed/* /home/pi/photos
fi;
chown -R pi /tmp/photos
chgrp -R pi /tmp/photos
((/home/pi/frame/frameserver.py --path /home/pi/photos 2>&1) & echo $! >&3) 3> $1 | multilog /var/log/frameserver &
