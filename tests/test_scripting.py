import neurocaas_contrib.scripting as scripting
import neurocaas_contrib.Interface_S3 as Interface_S3
import neurocaas_contrib.log as log
import localstack_client.session
import shlex
import json
import pytest
import os

loc = os.path.abspath(os.path.dirname(__file__))

localdata_dict = {
        "certificate_base":os.path.join(os.path.dirname(loc),"test_mats/certificate.txt"),
        "certificate_update":os.path.join(os.path.dirname(loc),"test_mats/certificate_update.txt"),
        "datastatus_base":os.path.join(os.path.dirname(loc),"test_mats/DATASET_NAME-dataset.ext_STATUS.txt.json"),
        "datastatus_update":os.path.join(os.path.dirname(loc),"test_mats/DATASET_NAME-dataset_update.ext_STATUS.txt.json")
        }

@pytest.mark.parametrize("field,value",[("scorer","kelly"),("task","iblright"),("jobnb","1"),("garbage",None)])
def test_get_yaml_field(field,value):
    test_yaml = os.path.join(loc,"test_mats","config.yaml")
    if value is not None:
        output =scripting.get_yaml_field(test_yaml,field)
        assert output == value
    else:    
        with pytest.raises(KeyError):
            output =scripting.get_yaml_field(test_yaml,field)

@pytest.mark.parametrize("name,value",[(os.path.join(loc,"test_mats","dir1.zip"),"pass"),(os.path.join(loc,"test_mats","dir2.zip"),"fail")])
def test_parse_zipfile(name,value):
    zippath = name
    if value == "pass":
        folder = scripting.parse_zipfile(zippath)
        assert folder == "dir1"
        assert os.path.exists(os.path.join(os.path.dirname(zippath),folder))
    elif value == "fail":
        folder = scripting.parse_zipfile(zippath)
        assert folder == "dir2"
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
       |-results  
         |-job__test
           |-logs
             |-certificate.txt
             |-DATASET_NAME-file.json_STATUS.json
             
    """
    bucketname = "testinterface"
    username = "user"
    statusname = "DATASET_NAME-file.json_STATUS.txt.json"
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
    monkeypatch.setattr(Interface_S3, "s3", session.resource("s3"))
    monkeypatch.setattr(log, "s3_resource", session.resource("s3")) ## TODO I don't think these are scoped correctly w/o a context manager.
    s3_client.create_bucket(Bucket = bucketname)
    for name,content in contents.items():
        key = os.path.join(username,name)
        writeobj = s3_resource.Object(bucketname,key)
        content = bytes(json.dumps(content).encode("UTF-8"))
        writeobj.put(Body = content)
    ## Now upload datastatus and certificate files:     
    s3_client.upload_file(os.path.join(loc,"test_mats",statusname),bucketname,os.path.join("user","results","job__test","logs",statusname))    
    s3_client.upload_file(os.path.join(loc,"test_mats","certificate.txt"),bucketname,os.path.join("user","results","job__test","logs","certificate.txt"))    
    return bucketname,username,contents,s3_client,s3_resource    

def test_log_process():        
    badscript = os.path.join(loc,"test_mats","sendtime_br.sh")
    goodscript = os.path.join(loc,"test_mats","sendtime.sh")
    logpath = os.path.join(loc,"test_mats","log","logfile.txt")

    brcode = scripting.log_process(shlex.split(badscript),logpath,"s3://fakepath/fakefile.txt")
    gdcode = scripting.log_process(shlex.split(goodscript),logpath,"s3://fakepath/fakefile.txt")
    assert brcode == 127
    assert gdcode == 0

@pytest.mark.skip
def test_register_data():    
    s3datapath = "s3://bucketname/groupname/inputs/data.txt"
    scripting.register_data(s3datapath)
    with open("./.neurocaas_contrib_dataconfig.json","r") as f: 
        z = json.load(f)
    assert z["datapath"] == s3datapath    
    os.remove("./.neurocaas_contrib_dataconfig.json")

@pytest.mark.skip
def test_register_config():    
    s3configpath = "s3://bucketname/groupname/configs/config.json"
    scripting.register_config(s3configpath)
    with open("./.neurocaas_contrib_dataconfig.json","r") as f: 
        z = json.load(f)
    assert z["configpath"] == s3configpath    
    os.remove("./.neurocaas_contrib_dataconfig.json")

@pytest.mark.skip
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
    
@pytest.mark.xfail #Not used     
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
        assert data["data"]["s3"] == "s3://bucket/groupname/inputs/filename.txt"    

    def test_register_dataset_local(self,tmp_path):
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        ncsm.register_data_local("groupname/inputs/filename.txt")
        with open(os.path.join(subdir,"registration.json"),"r") as fp:
            data = json.load(fp)
        assert data["data"]["localsource"] == "groupname/inputs/filename.txt"    

    def test_register_config(self,tmp_path):    
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        ncsm.register_config("s3://bucket/groupname/configs/filename.txt")
        with open(os.path.join(subdir,"registration.json"),"r") as fp:
            config = json.load(fp)
        assert config["config"]["s3"] == "s3://bucket/groupname/configs/filename.txt"    

    def test_register_config_local(self,tmp_path):    
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        ncsm.register_config_local("groupname/configs/filename.txt")
        with open(os.path.join(subdir,"registration.json"),"r") as fp:
            config = json.load(fp)
        assert config["config"]["localsource"] == "groupname/configs/filename.txt"    

    def test_register_file(self,tmp_path):    
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        ncsm.register_file("addfile","s3://bucket/groupname/configs/addfile.txt")
        with open(os.path.join(subdir,"registration.json"),"r") as fp:
            fi = json.load(fp)
        assert fi["additional_files"]["addfile"]["s3"] == "s3://bucket/groupname/configs/addfile.txt"    

    def test_register_file_local(self,tmp_path):    
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        ncsm.register_file_local("addfile","groupname/configs/addfile.txt")
        with open(os.path.join(subdir,"registration.json"),"r") as fp:
            fi = json.load(fp)
        assert fi["additional_files"]["addfile"]["localsource"] == "groupname/configs/addfile.txt"    

    def test_register_resultpath(self,tmp_path):    
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        ncsm.register_resultpath("s3://bucket/groupname/resuts/job__test/")

        with open(os.path.join(subdir,"registration.json"),"r") as fp:
            fi = json.load(fp)
        assert fi["resultpath"]["s3"] == "s3://bucket/groupname/resuts/job__test/"   

    def test_register_resultpath(self,tmp_path):    
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        ncsm.register_resultpath_local("groupname/resuts/job__test/")

        with open(os.path.join(subdir,"registration.json"),"r") as fp:
            fi = json.load(fp)
        assert fi["resultpath"]["localsource"] == "groupname/resuts/job__test/"   

    def test_from_registration(self,tmp_path):
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        ncsm2 = scripting.NeuroCAASScriptManager.from_registration(subdir)
        assert ncsm.registration == ncsm2.registration

    @pytest.mark.parametrize("source",["s3","local"])
    def test_get_data(self,tmp_path,setup_full_bucket,source):
        bucketname,username,contents,s3_client,s3_resource = setup_full_bucket
        contentkey = "inputs/file.json"
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        with pytest.raises(AssertionError):
            ncsm.get_data()
        if source == "s3":
            sourcepath = f"s3://{bucketname}/{username}/{contentkey}"
            ncsm.register_data(sourcepath)
        elif source == "local":
            sourcepath = tmp_path / f"{username}/{contentkey}"
            os.makedirs(os.path.dirname(sourcepath))
            with open(str(sourcepath),"w") as f:
                json.dump(contents[contentkey],f)
            ncsm.register_data_local(sourcepath)
        assert ncsm.get_data()
        assert ncsm.registration["data"]["local"] == str(subdir / "inputs" / "file.json") 
        assert not ncsm.get_data()
        assert ncsm.get_data(force = True)    
        assert ncsm.get_data(path = tmp_path)    
        assert ncsm.registration["data"]["local"] == str(tmp_path / "file.json") 
        assert not ncsm.get_data(path = tmp_path)


    @pytest.mark.parametrize("source",["s3","local"])
    def test_get_config(self,tmp_path,setup_full_bucket,source):
        bucketname,username,contents,s3_client,s3_resource = setup_full_bucket
        contentkey = "configs/config.json"
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        with pytest.raises(AssertionError):
            ncsm.get_config()
        if source == "s3":    
            sourcepath = f"s3://{bucketname}/{username}/{contentkey}"
            ncsm.register_config(sourcepath)
        elif source == "local":    
            sourcepath = tmp_path / f"{username}/{contentkey}"
            os.makedirs(os.path.dirname(sourcepath))
            with open(str(sourcepath),"w") as f:
                json.dump(contents[contentkey],f)
            ncsm.register_config_local(sourcepath)
        assert ncsm.get_config()
        assert ncsm.registration["config"]["local"] == str(subdir / "configs" / "config.json") 
        assert not ncsm.get_config()
        assert ncsm.get_config(force = True)    
        assert ncsm.get_config(path = tmp_path)    
        assert ncsm.registration["config"]["local"] == str(tmp_path / "config.json") 
        assert not ncsm.get_config(path = tmp_path)

    @pytest.mark.parametrize("source",["s3","local"])
    def test_get_file(self,tmp_path,setup_full_bucket,source):
        bucketname,username,contents,s3_client,s3_resource = setup_full_bucket
        contentkey = "inputs/extra.json"
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        filename = "extra"
        with pytest.raises(AssertionError):
            ncsm.get_file(filename)
        if source == "s3":    
            sourcepath = f"s3://{bucketname}/{username}/{contentkey}"
            ncsm.register_file(filename,sourcepath)
        elif source == "local":    
            sourcepath = tmp_path / f"{username}/{contentkey}"
            os.makedirs(os.path.dirname(sourcepath))
            with open(str(sourcepath),"w") as f:
                json.dump(contents[contentkey],f)
            ncsm.register_file_local(filename,sourcepath)
        assert ncsm.get_file(filename)
        assert ncsm.registration["additional_files"][filename]["local"] == str(subdir / "inputs" / "extra.json") 
        assert not ncsm.get_file(filename)
        assert ncsm.get_file(filename,force = True)    
        assert ncsm.get_file(filename,path = tmp_path)    
        assert ncsm.registration["additional_files"][filename]["local"] == str(tmp_path / "extra.json") 
        assert not ncsm.get_file(filename,path = tmp_path)

    @pytest.mark.parametrize("source",["s3","local"])
    def test_put_result(self,tmp_path,setup_full_bucket,source):    
        bucketname,username,contents,s3_client,s3_resource = setup_full_bucket
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        fullpath = subdir / "file.txt"
        fullpath.open("w")
        writepath = tmp_path / "outdir"
        writepath.mkdir()
        s3path = f"s3://{bucketname}/{username}/results/job__test"
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        with pytest.raises(AssertionError):
            ncsm.put_result(str(fullpath))
        if source == "s3":    
            ncsm.register_resultpath(s3path)
            ncsm.put_result(str(fullpath))
            loc =  s3_client.download_file(bucketname,f"{username}/results/job__test/process_results/file.txt",str(subdir / "file2.txt"))
        elif source == "local":    
            ncsm.register_resultpath_local(writepath)
            ncsm.put_result(str(fullpath))
            assert os.path.exists(os.path.join(writepath,"process_results",os.path.basename(fullpath)))
        
    def test_get_name(self,tmp_path):
        contents_empty = {"s3":None,"local":None}
        contents_remote = {"s3":"s3://bucket/group/inputs/key.txt","local":None}
        contents_full = {"s3":"s3://bucket/group/inputs/key.txt","local":"here/key.txt"}
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        with pytest.raises(AssertionError):
            ncsm.get_name(contents_empty)
        with pytest.raises(AssertionError):   
            nr = ncsm.get_name(contents_remote)
        nf = ncsm.get_name(contents_full)
        assert nf == "key.txt"

    def test_get_group(self,tmp_path):
        contents_empty = {"s3":None,"local":None}
        contents_remote = {"s3":"s3://bucket/group/inputs/key.txt","local":None}
        contents_full = {"s3":"s3://bucket/group/inputs/key.txt","local":"here/key.txt"}
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        with pytest.raises(AssertionError):
            ncsm.get_group(contents_empty)
        gr = ncsm.get_group(contents_remote)
        gf = ncsm.get_group(contents_full)
        assert gr == gf == "group" 
        
    def test_get_path(self,tmp_path):
        contents_empty = {"s3":None,"local":None}
        contents_remote = {"s3":"s3://bucket/group/inputs/key.txt","local":None}
        contents_full = {"s3":"s3://bucket/group/inputs/key.txt","local":"here/key.txt"}
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        with pytest.raises(AssertionError):
            ncsm.get_path(contents_empty)
        with pytest.raises(AssertionError):
            ncsm.get_path(contents_remote)
        pf = ncsm.get_path(contents_full)
        assert pf == "here/key.txt" 
   
    @pytest.mark.parametrize("filetype",["data","config","file"])
    def test_get_names(self,tmp_path,filetype,setup_full_bucket):
         subdir = tmp_path / "subdir"
         subdir.mkdir()    
         ncsm = scripting.NeuroCAASScriptManager(subdir)

         bucketname,username,contents,s3_client,s3_resource = setup_full_bucket
         if filetype == "data":
             contentkey = "inputs/file.json"
             s3path = f"s3://{bucketname}/{username}/{contentkey}"
             ncsm.register_data(s3path)
             ncsm.get_data()
             assert ncsm.get_dataname() == os.path.basename(contentkey)
         if filetype == "config":
             contentkey = "configs/config.json"
             s3path = f"s3://{bucketname}/{username}/{contentkey}"
             ncsm.register_config(s3path)
             ncsm.get_config()
             assert ncsm.get_configname() == os.path.basename(contentkey)
         if filetype == "file":
             contentkey = "inputs/extra.json"
             s3path = f"s3://{bucketname}/{username}/{contentkey}"
             name = "extra"
             ncsm.register_file(name,s3path)
             ncsm.get_file(name)
             assert ncsm.get_filename(name) == os.path.basename(contentkey)
        
    @pytest.mark.parametrize("filetype",["data","config","file"])
    def test_get_paths(self,tmp_path,filetype,setup_full_bucket):
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)

        bucketname,username,contents,s3_client,s3_resource = setup_full_bucket
        if filetype == "data":
            contentkey = "inputs/file.json"
            s3path = f"s3://{bucketname}/{username}/{contentkey}"
            ncsm.register_data(s3path)
            ncsm.get_data()
            assert ncsm.get_datapath() == os.path.join(subdir,"inputs",os.path.basename(contentkey))
        if filetype == "config":
            contentkey = "configs/config.json"
            s3path = f"s3://{bucketname}/{username}/{contentkey}"
            ncsm.register_config(s3path)
            ncsm.get_config()
            assert ncsm.get_configpath() == os.path.join(subdir,"configs",os.path.basename(contentkey))
        if filetype == "file":
            contentkey = "inputs/extra.json"
            s3path = f"s3://{bucketname}/{username}/{contentkey}"
            name = "extra"
            ncsm.register_file(name,s3path)
            ncsm.get_file(name)
            assert ncsm.get_filepath(name) == os.path.join(subdir,"inputs",os.path.basename(contentkey))

    def test_get_bucket_name(self,tmp_path,setup_full_bucket):
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)

        bucketname,username,contents,s3_client,s3_resource = setup_full_bucket
        contentkey = "inputs/file.json"
        s3path = f"s3://{bucketname}/{username}/{contentkey}"
        ncsm.register_data(s3path)
        ncsm.get_data()
        assert ncsm.get_bucket_name() == bucketname 

    def test_get_resultpath(self,tmp_path,setup_full_bucket):
        bucketname,username,contents,s3_client,s3_resource = setup_full_bucket
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        s3path = f"s3://{bucketname}/{username}/results/job__test"
        ncsm.register_resultpath(s3path)
        s3filepath = ncsm.get_resultpath("path/to/file.txt")
        s3dirpath = ncsm.get_resultpath("path/to/dir")
        assert s3filepath == os.path.join(s3path,"process_results","file.txt")
        assert s3dirpath == os.path.join(s3path,"process_results","dir")

    @pytest.mark.parametrize("logging",("local","s3"))
    def test_log_command(self,tmp_path,setup_full_bucket,logging):
        bucketname,username,contents,s3_client,s3_resource = setup_full_bucket
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)

        badscript = os.path.join(loc,"test_mats","sendtime_br.sh")
        goodscript = os.path.join(loc,"test_mats","sendtime.sh")
        logpath = os.path.join(loc,"test_mats","log")

        if logging == "local":
            brcode = ncsm.log_command(shlex.split(badscript),"s3://fake/fake/results/job__test/logs/DATASET_NAME-file.json_STATUS.txt.json")
            gdcode = ncsm.log_command(shlex.split(goodscript),"s3://fake/fake/results/job__test/logs/DATASET_NAME-file.json_STATUS.txt.json")
            assert "log.txt" in os.listdir(subdir / "logs")
            assert "certificate.txt" in os.listdir(subdir / "logs")
            with open(os.path.join(subdir,"logs","certificate.txt"),"r") as f:
                lines = f.readlines()
            assert lines[2].startswith("DATANAME: groupname/inputs/dataset.ext | STATUS: SUCCESS")

        if logging == "s3":
            brcode = ncsm.log_command(shlex.split(badscript),f"s3://{bucketname}/{username}/results/job__test/logs/DATASET_NAME-file.json_STATUS.txt.json")
            status = s3_client.download_file(bucketname,f"{username}/results/job__test/logs/DATASET_NAME-file.json_STATUS.txt.json",os.path.join(subdir,"status.json"))
            certificate = s3_client.download_file(bucketname,f"{username}/results/job__test/logs/certificate.txt",os.path.join(subdir,"certificate.txt"))

            with open(os.path.join(subdir,"certificate.txt"),"r") as f:
                lines = f.readlines()
            assert lines[2].startswith("DATANAME: groupname/inputs/dataset.ext | STATUS: FAILED")
            assert lines[10].startswith("WARNING: this is a template certificate")
            with open(os.path.join(subdir,"status.json"),"r") as f:
                status = json.load(f) 
            gdcode = ncsm.log_command(shlex.split(goodscript),f"s3://{bucketname}/{username}/results/job__test/logs/DATASET_NAME-file.json_STATUS.txt.json")
            status = s3_client.download_file(bucketname,f"{username}/results/job__test/logs/DATASET_NAME-file.json_STATUS.txt.json",os.path.join(subdir,"status.json"))
            certificate = s3_client.download_file(bucketname,f"{username}/results/job__test/logs/certificate.txt",os.path.join(subdir,"certificate.txt"))

            with open(os.path.join(subdir,"certificate.txt"),"r") as f:
                lines = f.readlines()
            assert lines[2].startswith("DATANAME: groupname/inputs/dataset.ext | STATUS: SUCCESS")
            assert lines[10].startswith("WARNING: this is a template certificate")
            with open(os.path.join(subdir,"status.json"),"r") as f:
                status = json.load(f) 

    def test_cleanup(self,tmp_path,setup_full_bucket):
        bucketname,username,contents,s3_client,s3_resource = setup_full_bucket
        s3path = f"s3://{bucketname}/{username}/results/job__test"
        contentkey = "configs/config.json"
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        ncsm.register_config(f"s3://{bucketname}/{username}/{contentkey}")
        ncsm.register_resultpath(s3path)
        ncsm.cleanup()
        update =  s3_client.download_file(bucketname,f"{username}/results/job__test/process_results/update.txt",str(subdir / "update.txt"))
        config =  s3_client.download_file(bucketname,f"{username}/results/job__test/process_results/config.json",str(subdir / "config.json"))
        

#modified tests based on assumption that input dir is passed, but data
#also uses download as usual but download_multi for get_data_multi case
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

    @pytest.mark.parametrize("input_path",["s3://bucket/groupname/inputs/filename.txt", 
                                           "s3://bucket/groupname/inputs"])
    def test_register_dataset(self,tmp_path,input_path):
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        ncsm.register_data(input_path)
        with open(os.path.join(subdir,"registration.json"),"r") as fp:
            data = json.load(fp)
        assert data["data"]["s3"] == input_path  

    @pytest.mark.parametrize("input_path",["groupname/inputs/filename.txt",
                                           "groupname/inputs"])
    def test_register_dataset_local(self,tmp_path,input_path):
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        ncsm.register_data_local(input_path)
        with open(os.path.join(subdir,"registration.json"),"r") as fp:
            data = json.load(fp)
        assert data["data"]["localsource"] == input_path 

    def test_register_config(self,tmp_path):    
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        ncsm.register_config("s3://bucket/groupname/configs/filename.txt")
        with open(os.path.join(subdir,"registration.json"),"r") as fp:
            config = json.load(fp)
        assert config["config"]["s3"] == "s3://bucket/groupname/configs/filename.txt"    

    def test_register_config_local(self,tmp_path):    
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        ncsm.register_config_local("groupname/configs/filename.txt")
        with open(os.path.join(subdir,"registration.json"),"r") as fp:
            config = json.load(fp)
        assert config["config"]["localsource"] == "groupname/configs/filename.txt"    

    def test_register_file(self,tmp_path):    
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        ncsm.register_file("addfile","s3://bucket/groupname/configs/addfile.txt")
        with open(os.path.join(subdir,"registration.json"),"r") as fp:
            fi = json.load(fp)
        assert fi["additional_files"]["addfile"]["s3"] == "s3://bucket/groupname/configs/addfile.txt"    

    def test_register_file_local(self,tmp_path):    
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        ncsm.register_file_local("addfile","groupname/configs/addfile.txt")
        with open(os.path.join(subdir,"registration.json"),"r") as fp:
            fi = json.load(fp)
        assert fi["additional_files"]["addfile"]["localsource"] == "groupname/configs/addfile.txt"    

    def test_register_resultpath(self,tmp_path):    
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        ncsm.register_resultpath("s3://bucket/groupname/resuts/job__test/")

        with open(os.path.join(subdir,"registration.json"),"r") as fp:
            fi = json.load(fp)
        assert fi["resultpath"]["s3"] == "s3://bucket/groupname/resuts/job__test/"   

    def test_register_resultpath(self,tmp_path):    
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        ncsm.register_resultpath_local("groupname/resuts/job__test/")

        with open(os.path.join(subdir,"registration.json"),"r") as fp:
            fi = json.load(fp)
        assert fi["resultpath"]["localsource"] == "groupname/resuts/job__test/"   

    def test_from_registration(self,tmp_path):
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        ncsm2 = scripting.NeuroCAASScriptManager.from_registration(subdir)
        assert ncsm.registration == ncsm2.registration

    @pytest.mark.parametrize("source",["s3","local"])
    def test_get_data(self,tmp_path,setup_full_bucket,source):
        bucketname,username,contents,s3_client,s3_resource = setup_full_bucket
        contentkey = "inputs/file.json"
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        with pytest.raises(AssertionError):
            ncsm.get_data()
        if source == "s3":
            sourcepath = f"s3://{bucketname}/{username}/{contentkey}"
            ncsm.register_data(sourcepath)
        elif source == "local":
            sourcepath = tmp_path / f"{username}/{contentkey}"
            os.makedirs(os.path.dirname(sourcepath))
            with open(str(sourcepath),"w") as f:
                json.dump(contents[contentkey],f)
            ncsm.register_data_local(sourcepath)
        # assert ncsm.get_data()
        # assert ncsm.registration["data"]["local"] == str(subdir / "inputs" / "file.json") 
        # assert not ncsm.get_data()
        # assert ncsm.get_data(force = True)    
        assert ncsm.get_data(path = tmp_path)    
        assert ncsm.registration["data"]["local"] == str(tmp_path / "file.json") 
        assert not ncsm.get_data(path = tmp_path)
        s3_resource.Bucket("testinterface").objects.all().delete()


    # registers the data via input dir path instead of file path
    @pytest.mark.parametrize("source",["local","s3"])
    def test_get_data_multi(self,tmp_path,setup_full_bucket,source):
        bucketname,username,contents,s3_client,s3_resource = setup_full_bucket
        contentdirkey = "inputs"
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        with pytest.raises(AssertionError):
            ncsm.get_data_multi()
        if source == "s3":
            sourcepath = f"s3://{bucketname}/{username}/{contentdirkey}"
            ncsm.register_data(sourcepath)
        elif source == "local":
            for key in contents.keys():
                if key.split("/")[0] == "inputs":
                    sourcepath = tmp_path / f"{username}/{key}"
                    if not os.path.exists(os.path.dirname(sourcepath)):
                        os.makedirs(os.path.dirname(sourcepath))
                    with open(str(sourcepath),"w") as f:
                        json.dump(contents[str(key)],f)
            ncsm.register_data_local(os.path.dirname(sourcepath))
        assert ncsm.get_data_multi()
        assert ncsm.registration["data"]["local"] == str(subdir / "inputs") 
        assert not ncsm.get_data_multi()
        assert ncsm.get_data_multi(force = True)   
        assert ncsm.get_data_multi(path = tmp_path)    
        assert ncsm.registration["data"]["local"] == str(tmp_path) 
        assert not ncsm.get_data_multi(path = tmp_path)


    @pytest.mark.parametrize("source",["s3","local"])
    def test_get_config(self,tmp_path,setup_full_bucket,source):
        bucketname,username,contents,s3_client,s3_resource = setup_full_bucket
        contentkey = "configs/config.json"
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        with pytest.raises(AssertionError):
            ncsm.get_config()
        if source == "s3":    
            sourcepath = f"s3://{bucketname}/{username}/{contentkey}"
            ncsm.register_config(sourcepath)
        elif source == "local":    
            sourcepath = tmp_path / f"{username}/{contentkey}"
            os.makedirs(os.path.dirname(sourcepath))
            with open(str(sourcepath),"w") as f:
                json.dump(contents[contentkey],f)
            ncsm.register_config_local(sourcepath)
        assert ncsm.get_config()
        assert ncsm.registration["config"]["local"] == str(subdir / "configs" / "config.json") 
        assert not ncsm.get_config()
        assert ncsm.get_config(force = True)    
        assert ncsm.get_config(path = tmp_path)    
        assert ncsm.registration["config"]["local"] == str(tmp_path / "config.json") 
        assert not ncsm.get_config(path = tmp_path)

    @pytest.mark.parametrize("source",["s3","local"])
    def test_get_file(self,tmp_path,setup_full_bucket,source):
        bucketname,username,contents,s3_client,s3_resource = setup_full_bucket
        contentkey = "inputs/extra.json"
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        filename = "extra"
        with pytest.raises(AssertionError):
            ncsm.get_file(filename)
        if source == "s3":    
            sourcepath = f"s3://{bucketname}/{username}/{contentkey}"
            ncsm.register_file(filename,sourcepath)
        elif source == "local":    
            sourcepath = tmp_path / f"{username}/{contentkey}"
            os.makedirs(os.path.dirname(sourcepath))
            with open(str(sourcepath),"w") as f:
                json.dump(contents[contentkey],f)
            ncsm.register_file_local(filename,sourcepath)
        assert ncsm.get_file(filename)
        assert ncsm.registration["additional_files"][filename]["local"] == str(subdir / "inputs" / "extra.json") 
        assert not ncsm.get_file(filename)
        assert ncsm.get_file(filename,force = True)    
        assert ncsm.get_file(filename,path = tmp_path)    
        assert ncsm.registration["additional_files"][filename]["local"] == str(tmp_path / "extra.json") 
        assert not ncsm.get_file(filename,path = tmp_path)

    @pytest.mark.parametrize("source",["s3","local"])
    def test_put_result(self,tmp_path,setup_full_bucket,source):    
        bucketname,username,contents,s3_client,s3_resource = setup_full_bucket
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        fullpath = subdir / "file.txt"
        fullpath.open("w")
        writepath = tmp_path / "outdir"
        writepath.mkdir()
        s3path = f"s3://{bucketname}/{username}/results/job__test"
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        with pytest.raises(AssertionError):
            ncsm.put_result(str(fullpath))
        if source == "s3":    
            ncsm.register_resultpath(s3path)
            ncsm.put_result(str(fullpath))
            loc =  s3_client.download_file(bucketname,f"{username}/results/job__test/process_results/file.txt",str(subdir / "file2.txt"))
        elif source == "local":    
            ncsm.register_resultpath_local(writepath)
            ncsm.put_result(str(fullpath))
            assert os.path.exists(os.path.join(writepath,"process_results",os.path.basename(fullpath)))
        
    def test_get_name(self,tmp_path):
        contents_empty = {"s3":None,"local":None}
        contents_remote = {"s3":"s3://bucket/group/inputs/key.txt","local":None}
        contents_full = {"s3":"s3://bucket/group/inputs/key.txt","local":"here/key.txt"}
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        with pytest.raises(AssertionError):
            ncsm.get_name(contents_empty)
        with pytest.raises(AssertionError):   
            nr = ncsm.get_name(contents_remote)
        nf = ncsm.get_name(contents_full)
        assert nf == "key.txt"

    def test_get_group(self,tmp_path):
        contents_empty = {"s3":None,"local":None}
        contents_remote = {"s3":"s3://bucket/group/inputs/key.txt","local":None}
        contents_full = {"s3":"s3://bucket/group/inputs/key.txt","local":"here/key.txt"}
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        with pytest.raises(AssertionError):
            ncsm.get_group(contents_empty)
        gr = ncsm.get_group(contents_remote)
        gf = ncsm.get_group(contents_full)
        assert gr == gf == "group" 
        
    def test_get_path(self,tmp_path):
        contents_empty = {"s3":None,"local":None}
        contents_remote = {"s3":"s3://bucket/group/inputs/key.txt","local":None}
        contents_full = {"s3":"s3://bucket/group/inputs/key.txt","local":"here/key.txt"}
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        with pytest.raises(AssertionError):
            ncsm.get_path(contents_empty)
        with pytest.raises(AssertionError):
            ncsm.get_path(contents_remote)
        pf = ncsm.get_path(contents_full)
        assert pf == "here/key.txt" 
   
    @pytest.mark.parametrize("filetype,datacontentkey",[("data","inputs"),("data","inputs/file.json"),("config","inputs"),("file","inputs")])
    def test_get_names(self,tmp_path,filetype,setup_full_bucket,datacontentkey):
         subdir = tmp_path / "subdir"
         subdir.mkdir()    
         ncsm = scripting.NeuroCAASScriptManager(subdir)

         bucketname,username,contents,s3_client,s3_resource = setup_full_bucket
         if filetype == "data":
             contentkey = datacontentkey
             s3path = f"s3://{bucketname}/{username}/{contentkey}"
             ncsm.register_data(s3path)

             if contentkey == "inputs/file.json":
                ncsm.get_data() 
                assert ncsm.get_dataname() == os.path.basename(contentkey)
             else:
                ncsm.get_data_multi()
                assert ncsm.get_dataname() == "inputs"
         if filetype == "config":
             contentkey = "configs/config.json"
             s3path = f"s3://{bucketname}/{username}/{contentkey}"
             ncsm.register_config(s3path)
             ncsm.get_config()
             assert ncsm.get_configname() == os.path.basename(contentkey)
         if filetype == "file":
             contentkey = "inputs/extra.json"
             s3path = f"s3://{bucketname}/{username}/{contentkey}"
             name = "extra"
             ncsm.register_file(name,s3path)
             ncsm.get_file(name)
             assert ncsm.get_filename(name) == os.path.basename(contentkey)
        
    @pytest.mark.parametrize("filetype,datacontentkey",[("data","inputs"),("data","inputs/file.json"),("config","inputs"),("file","inputs")])
    def test_get_paths(self,tmp_path,filetype,setup_full_bucket,datacontentkey):
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)

        bucketname,username,contents,s3_client,s3_resource = setup_full_bucket
        if filetype == "data":
            contentkey = datacontentkey
            s3path = f"s3://{bucketname}/{username}/{contentkey}"
            ncsm.register_data(s3path)
            if contentkey == "inputs/file.json":
                ncsm.get_data() 
                assert ncsm.get_datapath() == os.path.join(subdir,"inputs",os.path.basename(contentkey))
            else:
                ncsm.get_data_multi()
                assert ncsm.get_datapath() == os.path.join(subdir,"inputs")
           
        if filetype == "config":
            contentkey = "configs/config.json"
            s3path = f"s3://{bucketname}/{username}/{contentkey}"
            ncsm.register_config(s3path)
            ncsm.get_config()
            assert ncsm.get_configpath() == os.path.join(subdir,"configs",os.path.basename(contentkey))
        if filetype == "file":
            contentkey = "inputs/extra.json"
            s3path = f"s3://{bucketname}/{username}/{contentkey}"
            name = "extra"
            ncsm.register_file(name,s3path)
            ncsm.get_file(name)
            assert ncsm.get_filepath(name) == os.path.join(subdir,"inputs",os.path.basename(contentkey))

    @pytest.mark.parametrize("contentkey",["inputs","inputs/file.json"])
    def test_get_bucket_name(self,tmp_path,setup_full_bucket,contentkey):
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)

        bucketname,username,contents,s3_client,s3_resource = setup_full_bucket
        s3path = f"s3://{bucketname}/{username}/{contentkey}"
        ncsm.register_data(s3path)
        ncsm.get_data() if contentkey == "inputs/file.json" else ncsm.get_data_multi()
        assert ncsm.get_bucket_name() == bucketname 

    def test_get_resultpath(self,tmp_path,setup_full_bucket):
        bucketname,username,contents,s3_client,s3_resource = setup_full_bucket
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        s3path = f"s3://{bucketname}/{username}/results/job__test"
        ncsm.register_resultpath(s3path)
        s3filepath = ncsm.get_resultpath("path/to/file.txt")
        s3dirpath = ncsm.get_resultpath("path/to/dir")
        assert s3filepath == os.path.join(s3path,"process_results","file.txt")
        assert s3dirpath == os.path.join(s3path,"process_results","dir")

    @pytest.mark.parametrize("logging",["local","s3"])
    def test_log_command(self,tmp_path,setup_full_bucket,logging):
        bucketname,username,contents,s3_client,s3_resource = setup_full_bucket
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)

        badscript = os.path.join(loc,"test_mats","sendtime_br.sh")
        goodscript = os.path.join(loc,"test_mats","sendtime.sh")
        logpath = os.path.join(loc,"test_mats","log")

        if logging == "local":
            brcode = ncsm.log_command(shlex.split(badscript),"s3://fake/fake/results/job__test/logs/DATASET_NAME-file.json_STATUS.txt.json")
            gdcode = ncsm.log_command(shlex.split(goodscript),"s3://fake/fake/results/job__test/logs/DATASET_NAME-file.json_STATUS.txt.json")
            assert "log.txt" in os.listdir(subdir / "logs")
            assert "certificate.txt" in os.listdir(subdir / "logs")
            with open(os.path.join(subdir,"logs","certificate.txt"),"r") as f:
                lines = f.readlines()
            assert lines[2].startswith("DATANAME: groupname/inputs/dataset.ext | STATUS: SUCCESS")

        if logging == "s3":
            brcode = ncsm.log_command(shlex.split(badscript),f"s3://{bucketname}/{username}/results/job__test/logs/DATASET_NAME-file.json_STATUS.txt.json")
            status = s3_client.download_file(bucketname,f"{username}/results/job__test/logs/DATASET_NAME-file.json_STATUS.txt.json",os.path.join(subdir,"status.json"))
            certificate = s3_client.download_file(bucketname,f"{username}/results/job__test/logs/certificate.txt",os.path.join(subdir,"certificate.txt"))

            with open(os.path.join(subdir,"certificate.txt"),"r") as f:
                lines = f.readlines()
            assert lines[2].startswith("DATANAME: groupname/inputs/dataset.ext | STATUS: FAILED")
            assert lines[10].startswith("WARNING: this is a template certificate")
            with open(os.path.join(subdir,"status.json"),"r") as f:
                status = json.load(f) 
            gdcode = ncsm.log_command(shlex.split(goodscript),f"s3://{bucketname}/{username}/results/job__test/logs/DATASET_NAME-file.json_STATUS.txt.json")
            status = s3_client.download_file(bucketname,f"{username}/results/job__test/logs/DATASET_NAME-file.json_STATUS.txt.json",os.path.join(subdir,"status.json"))
            certificate = s3_client.download_file(bucketname,f"{username}/results/job__test/logs/certificate.txt",os.path.join(subdir,"certificate.txt"))

            with open(os.path.join(subdir,"certificate.txt"),"r") as f:
                lines = f.readlines()
            assert lines[2].startswith("DATANAME: groupname/inputs/dataset.ext | STATUS: SUCCESS")
            assert lines[10].startswith("WARNING: this is a template certificate")
            with open(os.path.join(subdir,"status.json"),"r") as f:
                status = json.load(f) 

    def test_cleanup(self,tmp_path,setup_full_bucket):
        bucketname,username,contents,s3_client,s3_resource = setup_full_bucket
        s3path = f"s3://{bucketname}/{username}/results/job__test"
        contentkey = "configs/config.json"
        subdir = tmp_path / "subdir"
        subdir.mkdir()    
        ncsm = scripting.NeuroCAASScriptManager(subdir)
        ncsm.register_config(f"s3://{bucketname}/{username}/{contentkey}")
        ncsm.register_resultpath(s3path)
        ncsm.cleanup()
        update =  s3_client.download_file(bucketname,f"{username}/results/job__test/process_results/update.txt",str(subdir / "update.txt"))
        config =  s3_client.download_file(bucketname,f"{username}/results/job__test/process_results/config.json",str(subdir / "config.json"))
