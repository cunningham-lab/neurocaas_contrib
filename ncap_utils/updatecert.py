## module to update the certificate.txt file
import boto3
import sys

def ls(bucket, path):
    """ Get all objects with bucket as strings"""
    return [
    objname.key for objname in bucket.objects.filter(Prefix=path)
    ]

def load_cert(bucket_name, key):
    """ """
    try:
        file_object = s3_resource.Object(bucket_name, key)
        raw_content = file_object.get()['Body'].read().decode('utf-8')
    except ValueError as ve:
        print("Error loading config file. Error is: {}".format(ve))
        raise ValueError
    return raw_content

if __name__ == "__main__":
    bucketname = sys.argv[1]
    resultspath = sys.argv[2]
    print(load_cert(bucketname,resultspath))

