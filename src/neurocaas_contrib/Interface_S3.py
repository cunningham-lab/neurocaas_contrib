'''
Script to download a video from the relevant amazon S3 bucket into a temporary diretory. 
'''
import sys
import os
import boto3 
from boto3.s3.transfer import S3Transfer 
import botocore 
import threading

s3 = boto3.resource('s3')
s3_client = boto3.client("s3")

## from https://stackoverflow.com/questions/41827963/track-download-progress-of-s3-file-using-boto3-and-callbacks
class ProgressPercentage_d(object):
    """Helper class to get and display percentage of data downloaded. 
    If display is set to false, assume that we're writing to a remote log file, and include newlines. 

    """
    def __init__(self,client,BUCKET,KEY,display = False):
        self._filename = KEY
        self._size = client.head_object(Bucket=BUCKET,Key=KEY)['ContentLength']
        self._seen_so_far = 0
        self._lock = threading.Lock()
        self.display = display

    def __call__(self,bytes_amount):
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = round((self._seen_so_far/self._size)*100,2)
            if self.display:
                sys.stdout.write(
                            "\r%s  %s / %s  (%.2f%%)" % (
                            self._filename, self._seen_so_far, self._size,
                            percentage))
                sys.stdout.flush()
            else:    
                sys.stdout.write(
                            "\r%s  %s / %s  (%.2f%%)\n" % (
                            self._filename, self._seen_so_far, self._size,
                            percentage))
                sys.stdout.flush()

class ProgressPercentage_u(object):
    """Helper class to get and display percentage of data uploaded. 
    If display is set to false, assume that we're writing to a remote log file, and include newlines. 

    """
    def __init__(self,FILEPATH,display = False):
        self._filename = FILEPATH
        self._size = float(os.path.getsize(FILEPATH)) 
        self._seen_so_far = 0
        self._lock = threading.Lock()
        self.display = display

    def __call__(self,bytes_amount):
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = round((self._seen_so_far/self._size)*100,2)
            if self.display:
                sys.stdout.write(
                            "\r%s  %s / %s  (%.2f%%)" % (
                            self._filename, self._seen_so_far, self._size,
                            percentage))
                sys.stdout.flush()
            else:    
                sys.stdout.write(
                            "\r%s  %s / %s  (%.2f%%)\n" % (
                            self._filename, self._seen_so_far, self._size,
                            percentage))
                sys.stdout.flush()

def download(s3path,localpath,display = False):
    """Download function. Takes an s3 path to an object, and local object path as input.   
    :param s3path: full path to an object in s3. Assumes the s3://bucketname/key syntax. 
    :param localpath: full path to the object name locally (i.e. with basename attached). 
    :param display: (optional) Defaults to false. If true, displays a progress bar. 

    """
    assert s3path.startswith("s3://")
    bucketname,keyname = s3path.split("s3://")[-1].split("/",1)

    try:
        transfer = S3Transfer(s3_client)
        progress = ProgressPercentage_d(transfer._manager._client,bucketname,keyname,display = display)
        transfer.download_file(bucketname,keyname,localpath,callback = progress)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("The object does not exist.")
            raise
        else:
            raise

def download_multi(s3path,localpath,force,display = False):
    """Download function. Takes an s3 path to a "folder" (path prefix that ends with backslack), and local object path as input. Will attempt to download all data at the given location to the local path.
    :param s3path: full path to an object in s3. Assumes the s3://bucketname/key syntax. 
    :param localpath: full path to the object name locally (i.e. with basename attached). 
    :param force: will not redownload if data of the same name already lives here
    :param display: (optional) Defaults to false. If true, displays a progress bar. 
    :return: bool (True if successful download, False otherwise)


    """
    assert s3path.startswith("s3://")
    bucketname,keyname = s3path.split("s3://")[-1].split("/",1)

    try:
        transfer = S3Transfer(s3_client)
        
        
        # adapted from https://stackoverflow.com/questions/49772151/download-a-folder-from-s3-using-boto3
        bucket = s3.Bucket(bucketname)
        for obj in bucket.objects.filter(Prefix = keyname):
            obj_keyname = obj.key
            if (os.path.basename(obj_keyname) in os.listdir(localpath)) and (not force):
                print("Data already exists at this location. Set force = true to overwrite")
                return 0
            progress = ProgressPercentage_d(transfer._manager._client,bucketname,obj_keyname,display = display)
            transfer.download_file(bucketname,obj_keyname,os.path.join(localpath,os.path.basename(obj_keyname)),callback = progress)
        return 1
            
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("The object does not exist.")
            raise
        else:
            raise

def upload(localpath,s3path,display = False):
    """Upload function. Takes a local object paht and s3 path to the desired key as input. 
    :param localpath: full path to the object name locally (i.e. with basename attached). 
    :param s3path: full path to an object in s3. Assumes the s3://bucketname/key syntax. 
    :param display: (optional) Defaults to false. If true, displays a progress bar. 

    """
    assert s3path.startswith("s3://")
    bucketname,keyname = s3path.split("s3://")[-1].split("/",1)

    try:
        transfer = S3Transfer(s3_client)
        progress = ProgressPercentage_u(localpath,display = display)
        transfer.upload_file(localpath,bucketname,keyname,callback = progress)

    except OSError as e:
        print("The file does not exist.")
        raise


