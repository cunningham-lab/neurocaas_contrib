#!/bin/bash
#set -e 
# usage: run.sh bucket path

# self.bucket_name, self.path, config.INDIR, config.OUTDIR, config.LOGDIR, self.data_filename, self.atlas_filename, self.params_filename

echo $1 >> $neurocaasrootdir/locanmf/check.txt # self.bucket_name
echo $2 >> $neurocaasrootdir/locanmf/check.txt # self.path
echo $3 >> $neurocaasrootdir/locanmf/check.txt # config.INDIR
echo $4 >> $neurocaasrootdir/locanmf/check.txt # config.OUTDIR
echo $5 >> $neurocaasrootdir/locanmf/check.txt # config.LOGDIR
echo $6 >> $neurocaasrootdir/locanmf/check.txt # self.data_filename
echo $7 >> $neurocaasrootdir/locanmf/check.txt # self.atlas_filename
echo $8 >> $neurocaasrootdir/locanmf/check.txt # self.params_filename

# Define Constants
TMPDIR=/home/ubuntu/tmp
INDIR=$TMPDIR/input/
OUTDIR=$TMPDIR/output/
LOGDIR=$TMPDIR/log/

# Make File Structure For Data, Results, and Logging
mkdir -p $INDIR
mkdir -p $OUTDIR
mkdir -p $LOGDIR

# Get Data & Config From Upload Bucket
#aws s3 sync s3://$1/$2/$3 $INDIR
aws s3 cp s3://$1/$2/$3/$6 $INDIR
aws s3 cp s3://$1/$2/configs/$8 $INDIR


# Activate Conda-Env
source /home/ubuntu/anaconda3/etc/profile.d/conda.sh
conda activate locaNMF

atlaspath=$(python $neurocaasrootdir/locanmf/parseyaml.py $INDIR/$8)
atlasname=$(basename $atlaspath)
aws s3 cp s3://$1/$atlaspath $INDIR

# Run command for periodic syncing of output and log folders to amazon s3 bucket, for monitoring purposes
$neurocaasrootdir/locanmf/sync_output.sh $OUTDIR $LOGDIR s3://$1/$2/$4/ s3://$1/$2/$5/ $TMPDIR &

# Run Python Script
python /home/ubuntu/locaNMF/run_locanmf.py $INDIR $OUTDIR $LOGDIR $6 $atlasname $8 >> $LOGDIR/log.txt

# Copy Results Back To S3 Subdirectory one last time
aws s3 sync $OUTDIR s3://$1/$2/$4/
aws s3 sync $LOGDIR s3://$1/$2/$5/

# Remove Temporary File Structure
#rm -rf $TMPDIR
#shutdown -h now
