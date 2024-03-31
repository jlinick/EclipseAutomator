#!/bin/bash

gphoto2 --set-config shutterspeed="1/250"
gphoto2 --stdout liveviewsize=0 --capture-movie | ffplay -

