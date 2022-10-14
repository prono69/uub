#!/usr/bin/env bash

sleep 5
[ -z $1 ] && exit 1
kill -9 $1
sleep 6
python3 -m pyUltroid