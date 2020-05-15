## module to update the certificate.txt file
import boto3
import json
import os
import sys
s3_resource = boto3.resource("s3")

def ls(bucket, path):
    """ Get all objects with bucket as strings"""
    return [
    objname.key.encode("utf-8") for objname in bucket.objects.filter(Prefix=path)
    ]

def load_cert(bucket_name, key):
    """ """
    try:
        file_object = s3_resource.Object(bucket_name, key)
        raw_content = file_object.get()['Body'].read() 
    except ValueError as ve:
        print("Error loading config file. Error is: {}".format(ve))
        raise ValueError
    return raw_content

if __name__ == "__main__":
    bucketname = sys.argv[1]
    bucket = s3_resource.Bucket(bucketname)
    resultspath = sys.argv[2]
    c = load_cert(bucketname,os.path.join(resultspath,"certificate.txt"))
    statusfiles = ls(bucket,os.path.join(resultspath,"DATASET_NAME"))
    names = []
    statuses = []
    for sfile in statusfiles:
        statusfile = load_cert(bucketname,sfile) 
        statusdict = json.loads(statusfile.decode("utf-8"))
        statuses.append(statusdict["status"])
        names.append(statusdict["input"])
    print(c+("\nDATASETS TO ANALYZE: \n {d1}: STATUS: {s1} \n {d2}: STATUS: {s2}".format(d1 = names[0],s1 = statuses[0],d2 = names[1], s2 = statuses[1])))
    print(statusdict)


