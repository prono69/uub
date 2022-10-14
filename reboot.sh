#!/usr/bin/env bash

[ -z $1 ] && exit 1
kill -9 $1
sleep 9
python3 -m pyUltroid