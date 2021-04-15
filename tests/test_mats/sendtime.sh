#!/bin/bash
# script to send current time to s3:
nowfile="/home/ubuntu/neurocaas_contrib/src/neurocaas_contrib/template_mats/nowfile.txt"

for i in {1..5}
do     
    sleep 1
    now=$(date)
    echo $now
done     
