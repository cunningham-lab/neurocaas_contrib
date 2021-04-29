import neurocaas_contrib.scripting as scripting
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
        

        
    

