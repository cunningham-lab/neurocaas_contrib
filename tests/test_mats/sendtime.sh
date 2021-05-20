#!/bin/bash
# script to send current time to s3:
nowfile="/home/ubuntu/neurocaas_contrib/src/neurocaas_contrib/template_mats/nowfile.txt"
source activate dgp

for i in {1..5}
do     
    sleep 0.1
    now=$(date)
    echo $now
done     
echo "Setting up network. This could take a while. "

cd "/Users/taigaabe/deepgraphpose/demo"

