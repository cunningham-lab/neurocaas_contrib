#!/bin/bash
set -e

userhome="/home/ubuntu"
datastore="neurocaas_webrtc/model"
configstore="neurocaas_webrtc/config"

echo "----DOWNLOADING DATA----"
neurocaas-contrib workflow get-data -f -o $userhome/$datastore/
neurocaas-contrib workflow get-config -f -o $userhome/$configstore/

datapath=$(neurocaas-contrib workflow get-datapath)
configpath=$(neurocaas-contrib workflow get-configpath)
taskname=$(tar -xvf "$datapath" -C "$userhome/$datastore")
echo "----DATA DOWNLOADED: $datapath. PARSING PARAMETERS.----"

echo "----RUNNING WEBRTC ----"
cd "$userhome/neurocaas_webrtc"
python server.py

# In case of want to finish process after some time
# python server.py &
# sleep 60
# kill $(pgrep -f 'python server.py')
# echo "DONE"
