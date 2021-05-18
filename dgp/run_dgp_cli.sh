#!/bin/bash
set -e
userhome="/home/ubuntu"
datastore="deepgraphpose/data"
outstore="ncapdata/localout"

echo "----DOWNLOADING DATA----"
source activate dgp
neurocaas-contrib workflow get-data -f -o $userhome/$datastore/
neurocaas-contrib workflow get-config -f -o $userhome/$datastore/

datapath=$(neurocaas-contrib workflow get-datapath)
configpath=$(neurocaas-contrib workflow get-configpath)
taskname=$(neurocaas-contrib scripting parse-zip -z "$datapath")
echo "----DATA DOWNLOADED: $datapath. PARSING PARAMETERS.----"

mode=$(neurocaas-contrib scripting read-yaml -p $configpath -f mode -d predict)
debug=$(neurocaas-contrib scripting read-yaml -p $configpath -f testing -d False)

echo "----RUNNING ANALYSIS IN MODE: $mode----"
cd "$userhome/deepgraphpose"

if [ $mode == "train" ]
then
    if [ $debug == "True" ]
    then
        echo "----STARTING TRAINING; SETTING UP DEBUG NETWORK----"
        python "demo/run_dgp_demo.py" --dlcpath "$userhome/$datastore/$taskname/" --test
    elif [ $debug == "False" ]    
    then 	
        echo "----STARTING TRAINING; SETTING UP NETWORK----"
        python "demo/run_dgp_demo.py" --dlcpath "$userhome/$datastore/$taskname/"
    else    
        echo "Debug setting $debug not recognized. Valid options are "True" or "False". Exiting."	
        exit
    fi    
    echo "----PREPARING RESULTS----"
    zip -r "/home/ubuntu/results_$taskname.zip" "$userhome/$datastore/$taskname/"
elif [ $mode == "predict" ]    
then
    if [ $debug == "True" ]
    then
        echo "----STARTING PREDICTION; SETTING UP DEBUG NETWORK----"
        python "demo/predict_dgp_demo.py" --dlcpath "$userhome/$datastore/$taskname/" --test
    elif [ $debug == "False" ]    
    then 	
        echo "----STARTING PREDICTION; SETTING UP NETWORK ----"
        python "demo/predict_dgp_demo.py" --dlcpath "$userhome/$datastore/$taskname/"
    else    
        echo "Debug setting $debug not recognized. Valid options are "True" or "False". Exiting."	
        exit
    fi    
    echo "----PREPARING RESULTS----"
    zip -r "/home/ubuntu/results_$taskname.zip" "$userhome/$datastore/$taskname/videos_pred/"
else    
    echo "Mode setting $mode not recognized. Valid options are "predict" or "train". Exiting."
fi

echo "----UPLOADING RESULTS----"
neurocaas-contrib workflow put-result -r "/home/ubuntu/results_$taskname.zip" -d 
