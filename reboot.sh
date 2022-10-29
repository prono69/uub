#!/usr/bin/env bash

sleep 6
[ -z $1 ] && exit 1
kill -9 $1
sleep 5
python3 -m pyUltroid