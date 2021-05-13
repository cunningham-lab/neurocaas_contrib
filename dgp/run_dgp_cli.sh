#!/bin/bash
userhome="/home/ubuntu"
datastore="deepgraphpose/data"
outstore="ncapdata/localout"

source activate dgp
neurocaas-contrib workflow get-data -d -f -o $userhome/$datastore/
neurocaas-contrib workflow get-config -d -f -o $userhome/$datastore/

datapath=$(neurocaas-contrib workflow get-datapath)
configpath=$(neurocaas-contrib workflow get-configpath)
taskname=$(neurocaas-contrib scripting parse-zip -z "$datapath")

mode=$(neurocaas-contrib scripting read-yaml -p $configpath -f mode -d predict)
debug=$(neurocaas-contrib scripting read-yaml -p $configpath -f testing -d False)

python "/home/ubuntu/neurocaas_contrib/dgp/project_path.py" "$userhome/$datastore/$taskname/config.yaml"

cd "$userhome/deepgraphpose"

if [ $mode == "train" ]
then
    if [ $debug == "True" ]
    then
        python "demo/run_dgp_demo.py" --dlcpath "$userhome/$datastore/$taskname/" --test
    elif [ $debug == "False" ]    
    then 	
        python "demo/run_dgp_demo.py" --dlcpath "$userhome/$datastore/$taskname/"
    else    
        echo "Debug setting $debug not recognized. Valid options are "True" or "False". Exiting."	
        exit
    zip -r "/home/ubuntu/results.zip" "$userhome/$datastore/$taskname/"
    fi    
elif [ $mode == "predict" ]    
then
    if [ $debug == "True" ]
    then
        python "demo/predict_dgp_demo.py" --dlcpath "$userhome/$datastore/$taskname/" --test
    elif [ $debug == "False" ]    
    then 	
        python "demo/predict_dgp_demo.py" --dlcpath "$userhome/$datastore/$taskname/"
    else    
        echo "Debug setting $debug not recognized. Valid options are "True" or "False". Exiting."	
        exit
    zip -r "/home/ubuntu/results.zip" "$userhome/$datastore/$taskname/videos_pred/"
    fi    
else    
    echo "Mode setting $mode not recognized. Valid options are "predict" or "train". Exiting."
fi

neurocaas-contrib workflow put-result -r "/home/ubuntu/results.zip" -d 
