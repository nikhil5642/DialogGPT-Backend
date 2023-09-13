#! /bin/bash

python3 -m server.fastApi.services &
/usr/local/bin/gunicorn --bind 0.0.0.0:5000 server.fastApi.app:app -w 2 -k uvicorn.workers.UvicornWorker --timeout 120 &
