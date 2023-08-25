import pytest
import json
import os
import localstack_client.session
import neurocaas_contrib.Interface_S3 as Interface_S3

@pytest.fixture
def setup_simple_bucket(monkeypatch):
    """Makes a simple bucket in localstack named testinterface with the following internal structure:  
    s3://testinterface
    |- user
     |-file.json
     |-config.json
    """
    bucketname = "testinterface"
    username = "user"
    contents = {
            "file.json":{"data":"element"},
            "config.json":{"param1":1},
            "another.json":{"please":"help"}
        }

    session = localstack_client.session.Session()
    s3_client = session.client("s3")
    s3_resource = session.resource("s3")
    monkeypatch.setattr(Interface_S3, "s3_client", session.client("s3")) ## TODO I don't think these are scoped correctly w/o a context manager.
    monkeypatch.setattr(Interface_S3, "s3", session.resource("s3"))
    s3_client.create_bucket(Bucket = bucketname)
    for name,content in contents.items():
        key = os.path.join(username,name)
        writeobj = s3_resource.Object(bucketname,key)
        content = bytes(json.dumps(content).encode("UTF-8"))
        writeobj.put(Body = content)
    return bucketname,username,contents,s3_client,s3_resource    

@pytest.fixture
def setup_complex_bucket(monkeypatch):
    """Makes a simple bucket in localstack named testinterface with the following internal structure:  
    s3://testinterface
    |- user
     |-file.json
     |-config.json
    """
    bucketname = "testinterface"
    username = "user"
    data_dirname = "inputs"
    config_dirname = "configs"
    contents_datasets = {
            "file.json":{"data":"element"},
            "another.json":{"please":"help"}
        }
    contents_configs = {
            "config.json":{"param1":1},
    }

    session = localstack_client.session.Session()
    s3_client = session.client("s3")
    s3_resource = session.resource("s3")
    monkeypatch.setattr(Interface_S3, "s3_client", session.client("s3")) ## TODO I don't think these are scoped correctly w/o a context manager.
    monkeypatch.setattr(Interface_S3, "s3", session.resource("s3"))
    s3_client.create_bucket(Bucket = bucketname)
    for name,content in contents_datasets.items():
        key = os.path.join(username,data_dirname,name)
        writeobj = s3_resource.Object(bucketname,key)
        content = bytes(json.dumps(content).encode("UTF-8"))
        writeobj.put(Body = content)
    for name,content in contents_configs.items():
        key = os.path.join(username,config_dirname,name)
        writeobj = s3_resource.Object(bucketname,key)
        content = bytes(json.dumps(content).encode("UTF-8"))
        writeobj.put(Body = content)
    return bucketname,username,data_dirname,config_dirname,s3_client,s3_resource    


# def test_download(setup_simple_bucket,tmp_path):
#     download_loc = tmp_path / "downloc"
#     download_loc.mkdir()
#     bucket,username,contents,s3_client,s3_resource = setup_simple_bucket
#     s3path = f"s3://{bucket}/{username}/file.json"
#     Interface_S3.download(s3path,str(download_loc / "config.json"))
#     Interface_S3.download(s3path,str(download_loc / "config.json"),display = True)
#     for obj in s3_resource.Bucket(bucket).objects.all():
#         print("\n" + str(obj))
#     print("\n\n\n\n")
#     for item in os.listdir(download_loc):
#         print("\n" + str(download_loc) + "/" + str(item))
#     s3_resource.Bucket("testinterface").objects.all().delete()


# def test_download_multi_simple(setup_simple_bucket,tmp_path):
#     download_loc = tmp_path / "downloc"
#     download_loc.mkdir()
#     bucket,username,contents,s3_client,s3_resource = setup_simple_bucket
#     s3path = f"s3://{bucket}/{username}"
#     Interface_S3.download_multi(s3path,str(download_loc))
#     # Interface_S3.download_multi(s3path,str(download_loc),display = True)
#     for obj in s3_resource.Bucket(bucket).objects.all():
#         print("\n" + str(obj))
#     print("\n\n\n\n")
#     for item in os.listdir(download_loc):
#         print("\n" + str(download_loc) + "/" + str(item))
#     s3_resource.Bucket("testinterface").objects.all().delete()

def test_download_multi_complex(setup_complex_bucket,tmp_path):
    download_loc = tmp_path / "downloc"
    download_loc.mkdir()
    bucket,username,data_dir,config_dir,s3_client,s3_resource = setup_complex_bucket
    s3path = f"s3://{bucket}/{username}/{data_dir}"
    Interface_S3.download_multi(s3path,str(download_loc))
    # Interface_S3.download_multi(s3path,str(download_loc),display = True)
    for obj in s3_resource.Bucket(bucket).objects.all():
        print("\n" + str(obj))
    print("\n\n\n\n")
    for item in os.listdir(download_loc):
        print("\n" + str(download_loc) + "/" + str(item))
    s3_resource.Bucket("testinterface").objects.all().delete()


# def test_upload(setup_simple_bucket,tmp_path):    
#     upload_loc = tmp_path / "uploc"
#     upload_loc.mkdir()
#     bucket,username,contents,s3_client,s3_resource = setup_simple_bucket
#     s3path = f"s3://{bucket}/{username}/up.json"
#     upload_file = str(os.path.join(upload_loc,"up.json"))
#     with open(upload_file,"w") as f:
#         json.dump({"up1":"item"},f)
#     Interface_S3.upload(upload_file,s3path)    
#     Interface_S3.upload(upload_file,s3path,display = True)    
#     Interface_S3.download(s3path,upload_file)
        




