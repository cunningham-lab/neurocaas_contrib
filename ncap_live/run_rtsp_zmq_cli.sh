#!/bin/bash
set -e

userhome="/home/ubuntu"
datafolder="dlclive-data"
project="DeepLabCut-live-GUI"

datastore="$datafolder/model"
configstore="$datafolder/config"
echo $datastore,$configstore

echo "----DOWNLOADING DATA----"
neurocaas-contrib workflow get-data -f -o $userhome/$datastore/
neurocaas-contrib workflow get-config -f -o $userhome/$configstore/

datapath=$(neurocaas-contrib workflow get-datapath)
configpath=$(neurocaas-contrib workflow get-configpath)
echo "----DATA DOWNLOADED: $datapath. PARSING PARAMETERS.----"

# Extract data and cfg file for DLCLive
echo "----EXTRACTING ZIP DATA---- "
unzip -o $datapath -d $userhome/$datastore
pathcfgfile=$(neurocaas-contrib scripting read-yaml -p $configpath -f path_cfg_file)
mv $userhome/$datastore/*.json $userhome/$pathcfgfile

tarfile=$(neurocaas-contrib scripting read-yaml -p $configpath -f model_file)
tar -xf "$userhome/$datastore/$tarfile" -C "$userhome/$datastore"
echo "----EXTRACTED MODEL $tarfile FOR DLCLIVE.----"

send=$(neurocaas-contrib scripting read-yaml -p $configpath -f send -d video)

echo "----RUNNING DLCLIVE-GUI SERVER WITH RTSP ----"
cd "$userhome/$project"
xvfb-run python run_simulation.py stream-zmq --send $send

# In case of want to finish process after some time
# xvfb-run python run_simulation.py stream-zmq --send $send &
# sleep 60
# kill $(pgrep -f "xvfb-run python run_simulation.py stream-zmq --send $send")
# echo "DONE"