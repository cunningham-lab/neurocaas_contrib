#!/bin/bash
# script to send current time to s3:
nowfile="/home/ubuntu/neurocaas_contrib/src/neurocaas_contrib/template_mats/nowfile.txt"

now=$(date)
echo $now > $nowfile

aws s3 cp $nowfile "s3://testfullpipeline/nowfile.txt"
