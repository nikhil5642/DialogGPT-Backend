#! /bin/bash
pkill gunicorn &
kill -9 `sudo lsof -t -i:5000` &
pkill -f server.fastApi.service 
