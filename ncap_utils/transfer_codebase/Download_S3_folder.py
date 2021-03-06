'''
Script to download videos from the relevant amazon S3 bucket into a temporary diretory. Old version just took parameter for source bucket "folder". New version (this one) takes additional parameter giving destination. This new version is more barebones, in that it does not ask for the config file (see commented out). Figure out the right way to structure this code.  
'''
import os
import sys
import boto3 
from boto3.s3.transfer import S3Transfer 
import botocore 
import threading
from Interface_S3 import download

if __name__ == "__main__":
    prekey = sys.argv[1]
    bucket_name = sys.argv[2]
    targetdir = sys.argv[3]
    ## List the contents of the directory in the S3 bucket: 
    s3 = boto3.resource('s3')
    my_bucket = s3.Bucket(bucket_name)
    for object in my_bucket.objects.filter(Prefix = prekey):
        if object.key[-1] != '/':
            download(bucket_name,object.key,tempdir = targetdir)



