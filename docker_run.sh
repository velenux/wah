#!/bin/bash

docker run -it --rm --name wah -e LANG=C.UTF-8 -v "$PWD":/usr/src/app -w /usr/src/app -e FLASK_APP=wah -p 5000:5000 wah
