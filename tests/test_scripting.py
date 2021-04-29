import neurocaas_contrib.scripting as scripting
import neurocaas_contrib.Interface_S3 as Interface_S3
import localstack_client.session
import shlex
import json
import pytest
import os

loc = os.path.abspath(os.path.dirname(__file__))

@pytest.mark.parametrize("field,value",[("scorer","kelly"),("task","iblright"),("jobnb","1"),("garbage",None)])
def test_get_yaml_field(field,value):
    test_yaml = os.path.join(loc,"test_mats","config.yaml")
    if value is not None:
        output =scripting.get_yaml_field(test_yaml,field)
        assert output == value
    else:    
        with pytest.raises(KeyError):
            output =scripting.get_yaml_field(test_yaml,field)

@pytest.mark.parametrize("name,value",[(os.path.join(loc,"../../ensembledata_3/zz.zip"),"pass"),(os.path.join(loc,"../../ensembledata_3/1.zip"),"fail")])
def test_parse_zipfile(name,value):
    zippath = name
    if value == "pass":
        folder = scripting.parse_zipfile(zippath)
        assert folder == "Reaching-Mackenzie-2018-08-30"
        assert os.path.exists(os.path.join(os.path.dirname(zippath),folder))
    elif value == "fail":
        folder = scripting.parse_zipfile(zippath)
        assert folder == "1"
        assert os.path.exists(os.path.join(os.path.dirname(zippath),folder))

@pytest.fixture
def setup_full_bucket(monkeypatch):
    """Makes a simple bucket in localstack named testinterface with the following internal structure:  
    s3://testinterface
    |- user
       |-inputs 
         |-file.json
         |-extra.json
       |-configs 
         |-config.json
    """
    bucketname = "testinterface"
    username = "user"
    contents = {
            "inputs/file.json":{"data":"element"},
            "inputs/extra.json":{"extra":"info"},
            "configs/config.json":{"param1":1}
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

def test_log_process():        
    badscript = os.path.join(loc,"test_mats","sendtime_br.sh")
    goodscript = os.path.join(loc,"test_mats","sendtime.sh")
    logpath = os.path.join(loc,"test_mats","log")

    brcode = scripting.log_process(shlex.split(badscript),"logpath","s3://fakepath")
    gdcode = scripting.log_process(shlex.split(goodscript),"logpath","s3://fakepath")
    assert brcode == 127
    assert gdcode == 0

def test_register_data():    
    s3datapath = "s3://bucketname/groupname/inputs/data.txt"
    scripting.register_data(s3datapath)
    with open("./.neurocaas_contrib_dataconfig.json","r") as f: 
        z = json.load(f)
    assert z["datapath"] == s3datapath    
    os.remove("./.neurocaas_contrib_dataconfig.json")

def test_register_config():    
    s3configpath = "s3://bucketname/groupname/configs/config.json"
    scripting.register_config(s3configpath)
    with open("./.neurocaas_contrib_dataconfig.json","r") as f: 
        z = json.load(f)
    assert z["configpath"] == s3configpath    
    os.remove("./.neurocaas_contrib_dataconfig.json")

@pytest.mark.parametrize("created",[["data"],["config"],["data","config"]])
def test_get_dataset_name(created):    
    if "data" in created:
        s3datapath = "s3://bucketname/groupname/inputs/data.txt"
        scripting.register_data(s3datapath)
    if "config" in created:    
        s3configpath = "s3://bucketname/groupname/configs/config.json"
        scripting.register_config(s3configpath)
    if "data" not in created:    
        with pytest.raises(Exception):
            data = scripting.get_dataset_name()    
    else:        
        data = scripting.get_dataset_name()    
        assert data == os.path.basename(s3datapath)
    os.remove("./.neurocaas_contrib_dataconfig.json")
    
@pytest.mark.parametrize("created",[["data"],["config"],["data","config"]])
def test_get_config_name(created):    
    if "data" in created:
        s3datapath = "s3://bucketname/groupname/inputs/data.txt"
        scripting.register_data(s3datapath)
    if "config" in created:    
        s3configpath = "s3://bucketname/groupname/configs/config.json"
        scripting.register_config(s3configpath)
    if "config" not in created:    
        with pytest.raises(Exception):
            config = scripting.get_config_name()    
    else:        
        data = scripting.get_config_name()    
        assert config == os.path.basename(s3configpath)
    os.remove("./.neurocaas_contrib_dataconfig.json")
    
class Test_NeuroCAASScriptManager():    
    def test_init(self,tmp_path):
        subdir = tmp_path / "subdir"
        with pytest.raises(AssertionError):
            ncsm = scripting.NeuroCAASScriptManager(subdir)
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir,write = False)
        assert not os.path.exists(os.path.join(subdir,"registration.json"))
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        assert os.path.exists(os.path.join(subdir,"registration.json"))

    def test_register_dataset(self,tmp_path):
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        ncsm.register_data("s3://bucket/groupname/inputs/filename.txt")
        with open(os.path.join(subdir,"registration.json"),"r") as fp:
            data = json.load(fp)
        data["data"]["s3"] == "s3://bucket/groupname/inputs/filename.txt"    

    def test_register_config(self,tmp_path):    
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        ncsm.register_config("s3://bucket/groupname/configs/filename.txt")
        with open(os.path.join(subdir,"registration.json"),"r") as fp:
            config = json.load(fp)
        config["config"]["s3"] == "s3://bucket/groupname/inputs/filename.txt"    

    def test_register_file(self,tmp_path):    
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        ncsm.register_file("addfile","s3://bucket/groupname/configs/addfile.txt")
        with open(os.path.join(subdir,"registration.json"),"r") as fp:
            fi = json.load(fp)
        fi["additional_files"]["addfile"]["s3"] == "s3://bucket/groupname/inputs/filename.txt"    

    def test_from_registration(self,tmp_path):
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        ncsm2 = scripting.NeuroCAASScriptManager.from_registration(subdir)
        assert ncsm.registration == ncsm2.registration

    def test_get_dataset(self,tmp_path,setup_full_bucket):
        bucketname,username,contents,s3_client,s3_resource = setup_full_bucket
        contentkey = "inputs/file.json"
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        s3path = f"s3://{bucketname}/{username}/{contentkey}"
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        with pytest.raises(AssertionError):
            ncsm.get_data()
        ncsm.register_data(s3path)
        ncsm.get_data()
        with pytest.raises(AssertionError):
            ncsm.get_data()
        ncsm.get_data(force = True)    
        ncsm.get_data(path = tmp_path)    
        with pytest.raises(AssertionError):
            ncsm.get_data(path = tmp_path)


    def test_get_config(self,tmp_path,setup_full_bucket):
        bucketname,username,contents,s3_client,s3_resource = setup_full_bucket
        contentkey = "configs/config.json"
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        s3path = f"s3://{bucketname}/{username}/{contentkey}"
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        with pytest.raises(AssertionError):
            ncsm.get_config()
        ncsm.register_config(s3path)
        ncsm.get_config()
        with pytest.raises(AssertionError):
            ncsm.get_config()
        ncsm.get_config(force = True)    
        ncsm.get_config(path = tmp_path)    
        with pytest.raises(AssertionError):
            ncsm.get_config(path = tmp_path)

    def test_get_file(self,tmp_path,setup_full_bucket):
        bucketname,username,contents,s3_client,s3_resource = setup_full_bucket
        contentkey = "inputs/extra.json"
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        s3path = f"s3://{bucketname}/{username}/{contentkey}"
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        filename = "extra"
        with pytest.raises(AssertionError):
            ncsm.get_file(filename)
        ncsm.register_file(filename,s3path)
        ncsm.get_file(filename)
        with pytest.raises(AssertionError):
            ncsm.get_file(filename)
        ncsm.get_file(filename,force = True)    
        ncsm.get_file(filename,path = tmp_path)    
        with pytest.raises(AssertionError):
            ncsm.get_file(filename,path = tmp_path)
        

        
    

