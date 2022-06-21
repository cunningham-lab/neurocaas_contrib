#!/bin/bash
set -e
## refactoring to depend on neurocaas-contrib
## From start to finish. 
userhome=$"/home/ubuntu"

call_read_label () {
    echo "compress labels for $1"	
    python read_manual_labels.py $1
}

call_proj_init () {
    echo "Project init $1"
    python "../neurocaas_ensembles/project_init.py"
}


echo -- CONFIGURING ENVIRONMENT  -- 

#source /home/ubuntu/.dlamirc
#
#export PATH="/home/ubuntu/anaconda3/bin:$PATH"
#
#source activate dgp

echo -- GETTING DATA AND PARAMETERS  -- 

neurocaas-contrib workflow get-data -f 
neurocaas-contrib workflow get-config -f 

echo -- PARSE PARAMETERS  -- 

dataname=$(neurocaas-contrib workflow get-dataname)
datapath=$(neurocaas-contrib workflow get-datapath)
configname=$(neurocaas-contrib workflow get-configname)
configpath=$(neurocaas-contrib workflow get-configpath)
groupname=$(neurocaas-contrib workflow get-group)
datastore=$(dirname $datapath)
configstore=$(dirname $configpath)
outstore=$(dirname $datastore)/results

## first unzip the training folder. 
## read in important metadata from config: 
mode=$(neurocaas-contrib scripting read-yaml -p "$configpath" -f mode -d predict)
testing=$(neurocaas-contrib scripting read-yaml -p "$configpath" -f "testing")
videotype=$(neurocaas-contrib scripting read-yaml -p "$configpath" -f "videotype")

cd "$userhome/deepgraphpose"
## Run dgp: 
if [ $mode == "train" ]
then
    echo -- UNZIPPING INITIAL MODEL  -- 
    datafolder=$(neurocaas-contrib scripting parse-zip -z "$datapath")
    ## get the manual labels: 
    echo -- INITIALIZING ENSEMBLE TRAINING PARAMS  -- 
    task="ensemble" #$(neurocaas-contrib scripting read-yaml -p "$configpath" -f "task")
    jobnb=$(neurocaas-contrib scripting read-yaml -p "$configpath" -f "jobnb")
    scorer="model$jobnb" #$(neurocaas-contrib scripting read-yaml -p "$configpath" -f "scorer")
    videotype=$(neurocaas-contrib scripting read-yaml -p "$configpath" -f "videotype")
    nb_frames=$(neurocaas-contrib scripting read-yaml -p "$configpath" -f "nb_frames" -d "")
    seed=$(neurocaas-contrib scripting read-yaml -p "$configpath" -f "seed" -d "")
    python /home/ubuntu/neurocaas_ensembles/read_manual_labels.py "$datastore/$datafolder" "$datastore" ".$videotype"
    ## This creates a folder called raw_data in the datastore folder. 
    #unzip -o "$userhome/$datastore/$dataname" -d "$userhome/$datastore/"
    
    
    ## create project from raw data: 
    python /home/ubuntu/neurocaas_ensembles/project_init.py "$task" "$scorer" "2030-01-0$jobnb" "$datastore/" "$nb_frames" "$seed"
    if [ $testing == "True" ]
    then
        echo -- STARTING TRAINING  -- 
        python "demo/run_dgp_demo.py" --dlcpath "$datastore/model_data/$task-$scorer-2030-01-0$jobnb/" --test
    elif [ $testing == "False" ]    
    then 	
        python "demo/run_dgp_demo.py" --dlcpath "$datastore/model_data/$task-$scorer-2030-01-0$jobnb/" 
    else    
        echo "Mode $testing not recognized. Valid options are "True" or "False". Exiting."	
        exit
    fi    
    resultpath=$(neurocaas-contrib workflow get-resultpath -l "$datastore/model_data/$task-$scorer-2030-01-0$jobnb/") 
    aws s3 sync "$datastore/model_data/$task-$scorer-2030-01-0$jobnb/" "$resultpath"

    zip -r "$userhome/contribdata/results$jobnb.zip" "$datastore/model_data/$task-$scorer-2030-01-0$jobnb/"
    neurocaas-contrib workflow put-result -r "$userhome/contribdata/results$jobnb.zip"  
elif [ $mode == "predict" ]
then
    echo -- GETTING ENSEMBLE MODELS FOR PREDICTION  -- 
    ## First, get all models and download them to this location. 
    topdir=$(neurocaas-contrib scripting read-yaml -p "$configpath" -f "modelpath")
    modeldirs=$(neurocaas-contrib scripting read-yaml -p "$configpath" -f "modelnames")
    datadir=$(dirname $datapath)
    ## Initialize local locations
    modelpaths=()
    for item in ${modeldirs};
    do 
        modelpath_s3=$groupname/$topdir$item ## topdir ends with divider. 	    
	modelpath_local=$datadir/$item
	aws s3 sync "s3://ensemble-dgp/"$modelpath_s3 $modelpath_local
	## copy video into modelfolders:
	modelpaths+=( $modelpath_local )
    done
    echo ${modelpaths[1]}
    echo ${modelpaths[@]}
    
    ## Next get the paths to individual models from the config file, and apply the config fix code. 	
    ## Next, 
    if [ $testing == "True" ]
    then
        echo "-- RUNNING PREDICTION (TEST) --"
	python $userhome/deepgraphpose/demo/predict_dgp_ensemble.py --modelpaths ${modelpaths[@]} --videopath $datapath
    elif [ $testing == "False" ]    
    then 	
        echo "-- RUNNING PREDICTION (REAL) --"
	python $userhome/deepgraphpose/demo/predict_dgp_ensemble.py --modelpaths ${modelpaths[@]} --videopath $datapath
    else    
        echo "Mode $testing not recognized. Valid options are "True" or "False". Exiting."	
        exit
    fi    
    echo "-- PREPARING RESULTS --"

    zip -r "$userhome/contribdata/consensus_results_$dataname.zip" "$userhome/contribdata/results/"
    neurocaas-contrib workflow put-result -r "$userhome/contribdata/consensus_results_$dataname.zip"  
else    
    echo "Mode setting $mode not recognized. Valid options are "predict" or "train". Exiting."
fi    

