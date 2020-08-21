#!/bin/sh
while :
do
	aws s3 sync $1 $2
	sleep 120
done
