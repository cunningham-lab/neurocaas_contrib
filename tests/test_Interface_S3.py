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
            "config.json":{"param1":1}
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

def test_download(setup_simple_bucket,tmp_path):
    download_loc = tmp_path / "downloc"
    download_loc.mkdir()
    bucket,username,contents,s3_client,s3_resource = setup_simple_bucket
    s3path = f"s3://{bucket}/{username}/file.json"
    Interface_S3.download(s3path,str(download_loc / "file.json"))
    Interface_S3.download(s3path,str(download_loc / "file.json"),display = True)

def test_upload(setup_simple_bucket,tmp_path):    
    upload_loc = tmp_path / "uploc"
    upload_loc.mkdir()
    bucket,username,contents,s3_client,s3_resource = setup_simple_bucket
    s3path = f"s3://{bucket}/{username}/up.json"
    upload_file = str(os.path.join(upload_loc,"up.json"))
    with open(upload_file,"w") as f:
        json.dump({"up1":"item"},f)
    Interface_S3.upload(upload_file,s3path)    
    Interface_S3.upload(upload_file,s3path,display = True)    
    Interface_S3.download(s3path,upload_file)
        




