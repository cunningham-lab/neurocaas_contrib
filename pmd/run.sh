#!/bin/sh
execpath="$0" # get path to this script
scriptpath="$neurocaasrootdir"/"ncap_utils" # get path to the utility library. 

## Import functions for workflow management. 
source "$scriptpath/workflow.sh" # import workflow management (monitoring, error finding) functions 
## Import functions for data transfer 
source "$scriptpath/transfer.sh" # import data transfer functions

## Set up error logging. 
errorlog #set up error logging

# usage: run.sh bucket path filename
# Define Constants
TMPDIR=/home/ubuntu/tmp
INDIR=$TMPDIR/input 
LOGDIR=$TMPDIR/log
OUTDIR=$TMPDIR/output

# Make File Structure For Data & Results
mkdir -p $INDIR
mkdir -p $LOGDIR
mkdir -p $OUTDIR

# Get Data & Config From Upload Bucket
#$1: bucket
#$2: path to inputs
#$3: dataset name 
#$4: path to configs
#$5: config name
#$6: results directory name. 
echo "aws s3 cp s3://${1}/${2}/${3} input"
echo "aws s3 cp s3://${1}/${4}/${5} config"
aws s3 cp s3://$1/$2/$3 $INDIR/
aws s3 cp s3://$1/$4/$5 $INDIR/


# Configure Anaconda For SSM (added by Miniconda3 4.5.12 installer)
__conda_setup="$(CONDA_REPORT_ERRORS=false '/home/ubuntu/miniconda3/bin/conda' shell.bash hook 2> /dev/null)"
if [ $? -eq 0 ]; then
	\eval "$__conda_setup"
else
	if [ -f "/home/ubuntu/miniconda3/etc/profile.d/conda.sh" ]; then
		. "/home/ubuntu/miniconda3/etc/profile.d/conda.sh"
		CONDA_CHANGEPS1=false conda activate base
	else
		\export PATH="/home/ubuntu/miniconda3/bin:$PATH"
	fi
fi
unset __conda_setup

# Start Subprocess To Continuously Sync Logdir
echo "$neurocaasrootdir/pmd/sync.sh $LOGDIR s3://${1}/${6}/logs &"
$neurocaasrootdir/pmd/sync.sh $LOGDIR s3://$1/$6/logs &

# Activate Conda-Env & Run Python Script
conda activate trefide
echo " -- Output From Denoiser -- " > $LOGDIR/pmd_out.txt	
python $neurocaasrootdir/pmd/compress.py $3 $INDIR $OUTDIR >> $LOGDIR/pmd_out.txt

# Copy Logs & Results Back To S3 Subdirectory
aws s3 sync $OUTDIR s3://$1/$6/process_results/
aws s3 sync $LOGDIR s3://$1/$6/logs/

# Remove Temporary File Structure
#rm -rf $TMPDIR

# Shutdown Instance
#shutdown -h now
