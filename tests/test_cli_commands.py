import pytest
import os
import shutil
from pathlib import Path
import traceback
import docker
from testpaths import get_dict_file 
from click.testing import CliRunner
import localstack_client
from botocore.errorfactory import ClientError
import neurocaas_contrib.remote
from neurocaas_contrib.cli_commands import *
from botocore.exceptions import ClientError
from neurocaas_contrib.local import default_neurocaas_repo
import neurocaas_contrib.monitor as monitor
import localstack_client.session
import neurocaas_contrib.Interface_S3 as Interface_S3

testdir = os.path.dirname(os.path.abspath(__file__))
test_log_mats = os.path.join(testdir,"test_mats","test_aws_resource","test_logfolder")

session = localstack_client.session.Session()
ec2_resource = session.resource("ec2")
ec2_client = session.client("ec2")
s3_client = session.client("s3")
s3 = session.resource("s3")
ssm_client = session.client("ssm")
sts = session.client("sts")

here  = os.path.dirname(__file__)

docker_client = docker.from_env()
session = localstack_client.session.Session()
s3_client = session.client("s3")
s3_resource = session.resource("s3")
 
def get_paths(rootpath):
    """Gets paths to all files relative to a given top level path. 

    """
    walkgen = os.walk(rootpath)
    paths = []
    dirpaths = []
    for p,dirs,files in walkgen:
        relpath = os.path.relpath(p,rootpath)
        if len(files) > 0 or len(dirs) > 0:
            for f in files:
                localfile = os.path.join(relpath,f)
                paths.append(localfile)
            ## We should upload the directories explicitly, as they will be treated in s3 like their own objects and we perform checks on them.    
            for d in dirs:
                localdir = os.path.join(relpath,d,"")
                if localdir == "./logs/":
                    dirpaths.append("logs/")
                else:
                    dirpaths.append(localdir)
    return paths,dirpaths            

test_log_mats = os.path.join(here,"test_mats","test_aws_resource","test_logfolder")
bucket_name = "test-log-analysis"
containername = "neurocaasdevcontainer"

def get_paths(rootpath):
    """Gets paths to all files relative to a given top level path. 

    """
    walkgen = os.walk(rootpath)
    paths = []
    dirpaths = []
    for p,dirs,files in walkgen:
        relpath = os.path.relpath(p,rootpath)
        if len(files) > 0 or len(dirs) > 0:
            for f in files:
                localfile = os.path.join(relpath,f)
                paths.append(localfile)
            ## We should upload the directories explicitly, as they will be treated in s3 like their own objects and we perform checks on them.    
            for d in dirs:
                localdir = os.path.join(relpath,d,"")
                if localdir == "./logs/":
                    dirpaths.append("logs/")
                else:
                    dirpaths.append(localdir)
    return paths,dirpaths            

@pytest.fixture
def remove_container(request):
    print(containername,"printing")
    yield "removing_container" 
    try:
        container = docker_client.containers.get(containername)
        container.remove(force=True)
    except:    
        pass

namedcontainername = "neurocaasdevcontainernamed"
@pytest.fixture
def remove_named_container(request):
    print(namedcontainername,"printing")
    yield "removing named container" 
    try:
        container = docker_client.containers.get(namedcontainername)
        container.remove(force=True)
    except:    
        pass

@pytest.fixture
def setup_log_bucket(monkeypatch):
    """Sets up the module to use localstack, and creates a bucket in localstack called test-log-analysis with the following directory structure:
    /
    |-logs
      |-bendeskylab
        |-joblog1
        |-joblog2
        ...
      |-sawtelllab
        |-joblog1
        |-joblog2
        ...
    This is the minimal working example for testing a monitoring function. This assumes that we will not be mutating the state of bucket logs. 
    """
    ## Start localstack and patch AWS clients:
    session = localstack_client.session.Session()
    monkeypatch.setattr(monitor, "s3_client", session.client("s3")) ## TODO I don't think these are scoped correctly w/o a context manager.
    monkeypatch.setattr(monitor, "s3_resource", session.resource("s3"))

    ## Create bucket if not created:
    try:
        buckets = s3_client.list_buckets()["Buckets"]
        bucketnames = [b["Name"] for b in buckets]
        assert bucket_name in bucketnames
        yield bucket_name
    except AssertionError:    
        s3_client.create_bucket(Bucket =bucket_name)

        ## Get paths:
        log_paths,dirpaths = get_paths(test_log_mats) 
        try:
            for f in log_paths:
                s3_client.upload_file(os.path.join(test_log_mats,f),bucket_name,Key = f)
            for dirpath in dirpaths:
                s3dir = s3_resource.Object(bucket_name,dirpath)   
                s3dir.put()
        except ClientError as e:        
            logging.error(e)
            raise
        yield bucket_name    
        ## Now delete 

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

@pytest.fixture
def mock_boto3_for_remote(monkeypatch):
    monkeypatch.setattr(neurocaas_contrib.remote,"ec2_resource",ec2_resource)
    monkeypatch.setattr(neurocaas_contrib.remote,"ec2_client",ec2_client)
    monkeypatch.setattr(neurocaas_contrib.remote,"s3",s3)
    monkeypatch.setattr(neurocaas_contrib.remote,"ssm_client",ssm_client)
    monkeypatch.setattr(neurocaas_contrib.remote,"sts",sts)
    instance = ec2_resource.create_instances(MaxCount = 1,MinCount=1)[0]
    ami = ec2_client.create_image(InstanceId=instance.instance_id,Name = "dummy")
    yield instance,ami["ImageId"]

def eprint(result):
    """Takes a result object returned by CliRunner.invoke, and prints full associated stack trace, including chained exceptions. Automatically throws an error if the exit code is not 0 to increase visibility of these errors.. Returns the result take as a parameter so this function can be used to wrap calls to invoke.  

    :param result: The output of CliRunner.invoke.

    """
    try:
        assert result.exit_code == 0
    except AssertionError:    
        traceback.print_exception(*result.exc_info)
        raise 
    return result

def test_cli():
    runner = CliRunner()
    result = runner.invoke(cli)
    assert result.exit_code == 0

@pytest.mark.parametrize("create,created",[("Y",True),("N",False)])
def test_cli_init(create,created):
    """Tests that the "init" subcommand correctly creates or does not create a new input file.

    """
    runner = CliRunner()
    name = "configure_fullsettings"
    with runner.isolated_filesystem():
        result = eprint(runner.invoke(cli,["init","--location","./","--analysis-name",name],input = create))
        assert os.path.exists("./"+name+"/stack_config_template.json")==created
    traceback.print_exception(*result.exc_info) ## this is pretty critical for active debugging. 

@pytest.mark.parametrize("create,created",[("Y",True),("N",False)])
def test_cli_init_noname(create,created):
    runner = CliRunner()
    name = "custom"
    with runner.isolated_filesystem():
        result = eprint(runner.invoke(cli,["init","--location","./"],input ="{}\n{}".format(name,create)))
        assert os.path.exists("./"+name+"/stack_config_template.json") == created

def test_cli_get_blueprint():
    runner = CliRunner()
    name = "getblueprint"
    with runner.isolated_filesystem():
        result = eprint(runner.invoke(cli,["init","--location","./"],input ="{}\n{}".format(name,"Y")))
        assert os.path.exists("./"+name+"/stack_config_template.json") == True
        result = eprint(runner.invoke(cli,["get-blueprint"]))
        outdict = json.loads(result.output)
    assert outdict["PipelineName"] == "templatestack"    
    keys = ["PipelineName","REGION","STAGE","Lambda","UXData"]
    for key in outdict.keys():
        assert key in keys

@pytest.mark.parametrize("initialized,info",[(False,["No info available."]),(True,["neurocaasdevcontainer (running)","neurocaas/test:base"])])
def test_cli_get_iae_info(remove_container,initialized,info):
    #TODO include way to test command. 
    runner = CliRunner()
    name = "getiaeinfo"
    with runner.isolated_filesystem():
        result = eprint(runner.invoke(cli,["init","--location","./"],input ="{}\n{}".format(name,"Y")))
        if initialized is True:
            result = eprint(runner.invoke(cli,["local","setup-development-container"]))
        result = eprint(runner.invoke(cli,["local","get-iae-info"]))
        outinfo = result.output
        for inf in info:
            assert inf in outinfo

def test_cli_setup_development_container(remove_container):
    runner = CliRunner()
    name = "setupimage"
    imagename = "neurocaas/test:base"

    with runner.isolated_filesystem():
        result = eprint(runner.invoke(cli,["init","--location","./"],input ="{}\n{}".format(name,"Y")))
        assert os.path.exists("./"+name+"/stack_config_template.json") == True
        result = eprint(runner.invoke(cli,["local","setup-development-container"]))
        with open("./"+name+"/stack_config_template.json") as f: 
            blueprint = json.load(f)
    assert blueprint["container_history"][-1] == containername
    assert blueprint["image_history"][-1] == imagename 

def test_cli_setup_development_container_named(remove_named_container):
    runner = CliRunner()
    name = "setupimage"
    imagename = "neurocaas/test:base"

    with runner.isolated_filesystem():
        result = eprint(runner.invoke(cli,["init","--location","./"],input ="{}\n{}".format(name,"Y")))
        assert os.path.exists("./"+name+"/stack_config_template.json") == True
        result = eprint(runner.invoke(cli,["local","setup-development-container","--image",imagename,"--container",namedcontainername]))
        with open("./"+name+"/stack_config_template.json") as f: 
            blueprint = json.load(f)
    assert blueprint["container_history"][-1] == namedcontainername
    assert blueprint["image_history"][-1] == imagename 

def test_cli_save_developed_image(remove_named_container):
    runner = CliRunner()
    name = "savedevelopedimage"
    imagerepo = "neurocaas/test"
    testid = "test01"

    with runner.isolated_filesystem():
        result = eprint(runner.invoke(cli,["init","--location","./"],input ="{}\n{}".format(name,"Y")))
        assert os.path.exists("./"+name+"/stack_config_template.json") == True
        result = eprint(runner.invoke(cli,["local","setup-development-container","--image",imagerepo,"--container",namedcontainername]))
        result = eprint(runner.invoke(cli,["local","save-developed-image","--tagid",testid,"--force","--container",namedcontainername]))
        with open("./"+name+"/stack_config_template.json") as f: 
            blueprint = json.load(f)
    imagetag = "{}:{}.{}".format(imagerepo,name,testid)
    try:
        docker_client.images.get(imagetag)
        docker_client.images.remove(imagetag)
    except docker.errors.ImageNotFound:
        assert 0
    assert blueprint["container_history"][-1] == namedcontainername
    assert blueprint["image_history"][-1] == imagetag

def test_cli_save_developed_image_script(remove_named_container):
    runner = CliRunner()
    name = "savedevelopedimage"
    imagerepo = "neurocaas/test"
    testid = "test01"
    script = "./run.sh"

    with runner.isolated_filesystem():
        result = eprint(runner.invoke(cli,["init","--location","./"],input ="{}\n{}".format(name,"Y")))
        assert os.path.exists("./"+name+"/stack_config_template.json") == True
        result = eprint(runner.invoke(cli,["local","setup-development-container","--image",imagerepo,"--container",namedcontainername]))
        result = eprint(runner.invoke(cli,["local","save-developed-image","--tagid",testid,"--force","--container",namedcontainername,"--script",script]))
        with open("./"+name+"/stack_config_template.json") as f: 
            blueprint = json.load(f)
        result = eprint(runner.invoke(cli,["local","get-iae-info"]))    
        assert script in result.output
    imagetag = "{}:{}.{}".format(imagerepo,name,testid)
    try:
        docker_client.images.get(imagetag)
        docker_client.images.remove(imagetag)
    except docker.errors.ImageNotFound:
        assert 0
    assert blueprint["container_history"][-1] == namedcontainername
    assert blueprint["image_history"][-1] == imagetag

def test_cli_describe_analyses():
    runner = CliRunner()
    name = "describeanalysis"
    name2= "describeanalysis2"
    
    with runner.isolated_filesystem():
        result = eprint(runner.invoke(cli,["init","--location","./"],input ="{}\n{}".format(name,"Y")))
        result = eprint(runner.invoke(cli,["init","--location","./"],input ="{}\n{}".format(name2,"Y")))
        result = eprint(runner.invoke(cli,["describe-analyses","--location","./"]))
    assert name in result.output   
    assert name2 in result.output   
    assert name2+"*" in result.output

def test_cli_setup_inputs():    
    runner = CliRunner()
    name = "setupinputs"
    datapath = "./data.txt"
    datapath2 = "./data2.txt"
    confpath = "./config.json"

    with runner.isolated_filesystem():
        Path(datapath).touch()
        Path(datapath2).touch()
        Path(confpath).touch()
        result = eprint(runner.invoke(cli,["init","--location","./"],input ="{}\n{}".format(name,"Y")))
        result = eprint(runner.invoke(cli,["local","setup-inputs","-d",datapath,"-d",datapath2,"-c",confpath]))
        assert os.path.exists(os.path.join("setupinputs","io-dir","inputs","data.txt"))
        assert os.path.exists(os.path.join("setupinputs","io-dir","inputs","data2.txt"))
        assert os.path.exists(os.path.join("setupinputs","io-dir","configs","config.json"))
        with open("./"+name+"/stack_config_template.json") as f: 
            blueprint = json.load(f)
    assert blueprint["localenv"] == "./setupinputs"      

def test_container_singleton(remove_named_container):
    runner = CliRunner()
    name = "resetcontainer"

    with runner.isolated_filesystem():
        result = eprint(runner.invoke(cli,["init","--location","./"],input ="{}\n{}".format(name,"Y")))
        result = eprint(runner.invoke(cli,["local","setup-development-container","--container",namedcontainername]))
        with pytest.raises(Exception):
            result = eprint(runner.invoke(cli,["local","setup-development-container","--container",namedcontainername]))

def test_reset_container(remove_named_container):            
    runner = CliRunner()
    name = "resetcontainer"
    with runner.isolated_filesystem():
        result = eprint(runner.invoke(cli,["init","--location","./"],input ="{}\n{}".format(name,"Y")))
        result = eprint(runner.invoke(cli,["local","reset-container","--container",namedcontainername]))
        result = eprint(runner.invoke(cli,["local","setup-development-container","--container",namedcontainername]))

@pytest.mark.xfail ## issue with docker volumes in the runner isolated filesystem
def test_cli_setup_development_container_env(remove_named_container):
    runner = CliRunner()
    name = "setupimage_env"
    imagename = "neurocaas/test:base"
    datapath = "./data.txt"
    datapath2 = "./data2.txt"
    confpath = "./config.json"

    with runner.isolated_filesystem():
        Path(datapath).touch()
        Path(datapath2).touch()
        Path(confpath).touch()
        result = eprint(runner.invoke(cli,["init","--location","./"],input ="{}\n{}".format(name,"Y")))
        result = eprint(runner.invoke(cli,["local","setup-inputs","-d",datapath,"-d",datapath2,"-c",confpath]))
        assert os.path.exists("./"+name+"/stack_config_template.json") == True
        result = eprint(runner.invoke(cli,["local","setup-development-container","--image",imagename,"--container",namedcontainername]))
        with open("./"+name+"/stack_config_template.json") as f: 
            blueprint = json.load(f)
    assert blueprint["container_history"][-1] == namedcontainername
    assert blueprint["image_history"][-1] == imagename 

### Test monitoring functions. 
@pytest.mark.skipif(get_dict_file() == "ci",reason = "Skipping test that relies on logs.")
def test_visualize_parallelism(setup_log_bucket):
    bucket_name = setup_log_bucket
    runner = CliRunner()
    with runner.isolated_filesystem():
        os.mkdir("./logs")
        result = eprint(runner.invoke(cli,["init","--location","./"],input = "{}\n{}".format(bucket_name,"Y")))
        result = eprint(runner.invoke(cli,["visualize-parallelism","-p","./logs"]))
        logfiles = os.listdir("./logs")
        assert len(logfiles) == 2
        labnames = ["bendeskylab","sawtelllab"]
        for l in logfiles:
            assert any([l.startswith(bucket_name+"_{}".format(f)) for f in labnames])
            assert l.endswith("_parallel_logs.json")
            with open(os.path.join("./logs",l),"r") as f:
                jobdict = json.load(f)
            ## caclualte number of instances:     
            count = 0
            for job in jobdict.values():
                count += len(job["instances"])
            if any([k.startswith("bendesky") for k in jobdict.keys()]):    
                assert count == 157
            elif any([k.startswith("sawtell") for k in jobdict.keys()]):    
                assert count == 132




class Test_workflow():    
    def test_workflow(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = eprint(runner.invoke(cli,["workflow"]))

    def test_initialize_job(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = eprint(runner.invoke(cli,["workflow","initialize-job","-p", "./"]))
            with open("./.neurocaas_contrib_storageloc_test.json", "r") as f:
                storage = json.load(f)
            assert storage["path"] == os.path.abspath("./")
            assert os.path.exists("./registration.json")

    def test_register_dataset(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            with pytest.raises(AssertionError):
                result = eprint(runner.invoke(cli,["workflow","register-dataset","-b","bucketname","-p","keypath/key.txt"]))
            result = eprint(runner.invoke(cli,["workflow","initialize-job","-p", "./"]))
            with open("./.neurocaas_contrib_storageloc_test.json", "r") as f:
                storage = json.load(f)
            assert storage["path"] == os.path.abspath("./")
            print(os.path.abspath("./"))
            result = eprint(runner.invoke(cli,["workflow","register-dataset","-b","bucketname","-k","keypath/key.txt"]))
            assert os.path.exists("./registration.json")
            with open("./registration.json") as f:
                reg = json.load(f)
            assert reg["data"]["s3"] == "s3://bucketname/keypath/key.txt"    

    def test_register_config(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            with pytest.raises(AssertionError):
                result = eprint(runner.invoke(cli,["workflow","register-config","-b","bucketname","-k","keypath/key.txt"]))
            result = eprint(runner.invoke(cli,["workflow","initialize-job","-p", "./"]))
            with open("./.neurocaas_contrib_storageloc_test.json", "r") as f:
                storage = json.load(f)
            assert storage["path"] == os.path.abspath("./")
            print(os.path.abspath("./"))
            result = eprint(runner.invoke(cli,["workflow","register-config","-b","bucketname","-k","keypath/key.txt"]))
            assert os.path.exists("./registration.json")
            with open("./registration.json") as f:
                reg = json.load(f)
            assert reg["config"]["s3"] == "s3://bucketname/keypath/key.txt"    
            
    def test_register_file(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            with pytest.raises(AssertionError):
                result = eprint(runner.invoke(cli,["workflow","register-file","-n","filename","-b","bucketname","-k","keypath/key.txt"]))
            result = eprint(runner.invoke(cli,["workflow","initialize-job","-p", "./"]))
            with open("./.neurocaas_contrib_storageloc_test.json", "r") as f:
                storage = json.load(f)
            assert storage["path"] == os.path.abspath("./")
            print(os.path.abspath("./"))
            result = eprint(runner.invoke(cli,["workflow","register-file","-n","filename","-b","bucketname","-k","keypath/key.txt"]))
            assert os.path.exists("./registration.json")
            with open("./registration.json") as f:
                reg = json.load(f)
            assert reg["additional_files"]["filename"]["s3"] == "s3://bucketname/keypath/key.txt"    
            
    def test_register_resultpath(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            with pytest.raises(AssertionError):
                result = eprint(runner.invoke(cli,["workflow","register-resultpath","-b","bucketname","-k","keypath/"]))
            result = eprint(runner.invoke(cli,["workflow","initialize-job","-p", "./"]))
            with open("./.neurocaas_contrib_storageloc_test.json", "r") as f:
                storage = json.load(f)
            assert storage["path"] == os.path.abspath("./")
            print(os.path.abspath("./"))
            result = eprint(runner.invoke(cli,["workflow","register-resultpath","-b","bucketname","-k","keypath/"]))
            assert os.path.exists("./registration.json")
            with open("./registration.json") as f:
                reg = json.load(f)
            assert reg["resultpath"] == "s3://bucketname/keypath/"    

    def test_get_data(self,setup_simple_bucket):
        runner = CliRunner()
        with runner.isolated_filesystem():
            with pytest.raises(AssertionError):
                result = eprint(runner.invoke(cli,["workflow","get-data","-o","outputpath","-f","-d"]))
            result = eprint(runner.invoke(cli,["workflow","initialize-job","-p", "./"]))
            with open("./.neurocaas_contrib_storageloc_test.json", "r") as f:
                storage = json.load(f)
            assert storage["path"] == os.path.abspath("./")
            print(os.path.abspath("./"))
            result = eprint(runner.invoke(cli,["workflow","register-dataset","-b","testinterface","-k","user/file.json"]))
            result = eprint(runner.invoke(cli,["workflow","get-data"]))
            assert os.path.exists("./inputs/file.json") 
            ## now make sure it's not changed if we don't force: 
            with open("./inputs/file.json","r") as f:
                d = json.load(f)
                d["data"] = "element2"
            with open("./inputs/file.json","w") as f:
                json.dump(d,f)
            result = eprint(runner.invoke(cli,["workflow","get-data"]))
            with open("./inputs/file.json","r") as f:
                d = json.load(f)
                assert d["data"] == "element2"
            result = eprint(runner.invoke(cli,["workflow","get-data","-f"]))
            with open("./inputs/file.json","r") as f:
                d = json.load(f)
                assert d["data"] == "element"
            result = eprint(runner.invoke(cli,["workflow","get-data","-o","./"]))
            assert os.path.exists("./file.json") 
            with open("./file.json","r") as f:
                d = json.load(f)
                d["data"] = "element2"
            with open("./file.json","w") as f:
                json.dump(d,f)
            result = eprint(runner.invoke(cli,["workflow","get-data","-o","./"]))
            with open("./file.json","r") as f:
                d = json.load(f)
                assert d["data"] == "element2"
            result = eprint(runner.invoke(cli,["workflow","get-data","-f","-o","./"]))
            with open("./inputs/file.json","r") as f:
                d = json.load(f)
                assert d["data"] == "element"

    def test_get_config(self,setup_simple_bucket):
        runner = CliRunner()
        with runner.isolated_filesystem():
            with pytest.raises(AssertionError):
                result = eprint(runner.invoke(cli,["workflow","get-config","-o","outputpath","-f","-d"]))
            result = eprint(runner.invoke(cli,["workflow","initialize-job","-p", "./"]))
            with open("./.neurocaas_contrib_storageloc_test.json", "r") as f:
                storage = json.load(f)
            assert storage["path"] == os.path.abspath("./")
            print(os.path.abspath("./"))
            result = eprint(runner.invoke(cli,["workflow","register-config","-b","testinterface","-k","user/config.json"]))
            result = eprint(runner.invoke(cli,["workflow","get-config"]))
            assert os.path.exists("./configs/config.json") 
            ## now make sure it's not changed if we don't force: 
            with open("./configs/config.json","r") as f:
                d = json.load(f)
                d["param1"] = "element2"
            with open("./configs/config.json","w") as f:
                json.dump(d,f)
            result = eprint(runner.invoke(cli,["workflow","get-config"]))
            with open("./configs/config.json","r") as f:
                d = json.load(f)
                assert d["param1"] == "element2"
            result = eprint(runner.invoke(cli,["workflow","get-config","-f"]))
            with open("./configs/config.json","r") as f:
                d = json.load(f)
                assert d["param1"] == 1 
            result = eprint(runner.invoke(cli,["workflow","get-config","-o","./"]))
            assert os.path.exists("./config.json") 
            with open("./config.json","r") as f:
                d = json.load(f)
                d["param1"] = "element2"
            with open("./config.json","w") as f:
                json.dump(d,f)
            result = eprint(runner.invoke(cli,["workflow","get-config","-o","./"]))
            with open("./config.json","r") as f:
                d = json.load(f)
                assert d["param1"] == "element2"
            result = eprint(runner.invoke(cli,["workflow","get-config","-f","-o","./"]))
            with open("./configs/config.json","r") as f:
                d = json.load(f)
                assert d["param1"] == 1

    def test_get_file(self,setup_simple_bucket):
        runner = CliRunner()
        with runner.isolated_filesystem():
            with pytest.raises(AssertionError):
                result = eprint(runner.invoke(cli,["workflow","get-file","-n","filename","-o","outputpath","-f","-d"]))
            result = eprint(runner.invoke(cli,["workflow","initialize-job","-p", "./"]))
            with open("./.neurocaas_contrib_storageloc_test.json", "r") as f:
                storage = json.load(f)
            assert storage["path"] == os.path.abspath("./")
            print(os.path.abspath("./"))
            result = eprint(runner.invoke(cli,["workflow","register-file","-n","addfile","-b","testinterface","-k","user/file.json"]))
            result = eprint(runner.invoke(cli,["workflow","get-file","-n","addfile"]))
            assert os.path.exists("./inputs/file.json") 
            ## now make sure it's not changed if we don't force: 
            with open("./inputs/file.json","r") as f:
                d = json.load(f)
                d["data"] = "element2"
            with open("./inputs/file.json","w") as f:
                json.dump(d,f)
            result = eprint(runner.invoke(cli,["workflow","get-file","-n","addfile"]))
            with open("./inputs/file.json","r") as f:
                d = json.load(f)
                assert d["data"] == "element2"
            result = eprint(runner.invoke(cli,["workflow","get-file","-n","addfile","-f"]))
            with open("./inputs/file.json","r") as f:
                d = json.load(f)
                assert d["data"] == "element"
            result = eprint(runner.invoke(cli,["workflow","get-file","-n","addfile","-o","./"]))
            assert os.path.exists("./file.json") 
            with open("./file.json","r") as f:
                d = json.load(f)
                d["data"] = "element2"
            with open("./file.json","w") as f:
                json.dump(d,f)
            result = eprint(runner.invoke(cli,["workflow","get-file","-n","addfile","-o","./"]))
            with open("./file.json","r") as f:
                d = json.load(f)
                assert d["data"] == "element2"
            result = eprint(runner.invoke(cli,["workflow","get-file","-n","addfile","-f","-o","./"]))
            with open("./inputs/file.json","r") as f:
                d = json.load(f)
                assert d["data"] == "element"

    def test_put_result(self,setup_simple_bucket):
        bucketname,username,contents,s3_client,s3_resource = setup_simple_bucket
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("file.txt","w") as f:
                f.close()
            with pytest.raises(AssertionError):
                result = eprint(runner.invoke(cli,["workflow","put-result","-r","file.txt","-d"]))
            result = eprint(runner.invoke(cli,["workflow","initialize-job","-p", "./"]))
            with open("./.neurocaas_contrib_storageloc_test.json", "r") as f:
                storage = json.load(f)
            assert storage["path"] == os.path.abspath("./")
            result = eprint(runner.invoke(cli,["workflow","register-resultpath","-b",bucketname,"-k","keypath/"]))
            result = eprint(runner.invoke(cli,["workflow","put-result","-r","file.txt","-d"]))
            config =  s3_client.download_file(bucketname,"keypath/process_results/file.txt","./file.txt")

    def test_get_dataname(self,setup_simple_bucket):            
        runner = CliRunner()
        with runner.isolated_filesystem():
            with pytest.raises(AssertionError):
                result = eprint(runner.invoke(cli,["workflow","get-dataname"]))
            result = eprint(runner.invoke(cli,["workflow","initialize-job","-p", "./"]))
            result = eprint(runner.invoke(cli,["workflow","register-dataset","-b","testinterface","-k","user/file.json"]))
            with pytest.raises(AssertionError):#assert result.output == "file.json"
                dataname = eprint(runner.invoke(cli,["workflow","get-dataname"]))
            result = eprint(runner.invoke(cli,["workflow","get-data"]))
            dataname = eprint(runner.invoke(cli,["workflow","get-dataname"]))
            print(dataname.output,"all output")
            assert dataname.output == "file.json\n"

    def test_get_configname(self,setup_simple_bucket):            
        runner = CliRunner()
        with runner.isolated_filesystem():
            with pytest.raises(AssertionError):
                result = eprint(runner.invoke(cli,["workflow","get-configname"]))
            result = eprint(runner.invoke(cli,["workflow","initialize-job","-p", "./"]))
            result = eprint(runner.invoke(cli,["workflow","register-config","-b","testinterface","-k","user/config.json"]))
            with pytest.raises(AssertionError):#assert result.output == "file.json"
                configname = eprint(runner.invoke(cli,["workflow","get-configname"]))
            result = eprint(runner.invoke(cli,["workflow","get-config"]))
            configname = eprint(runner.invoke(cli,["workflow","get-configname"]))
            print(configname.output,"all output")
            assert configname.output == "config.json\n"

    def test_get_filename(self,setup_simple_bucket):            
        runner = CliRunner()
        with runner.isolated_filesystem():
            with pytest.raises(AssertionError):
                result = eprint(runner.invoke(cli,["workflow","get-filename"]))
            result = eprint(runner.invoke(cli,["workflow","initialize-job","-p", "./"]))
            result = eprint(runner.invoke(cli,["workflow","register-file","-n","namevar","-b","testinterface","-k","user/file.json"]))
            #assert result.output == "file.json"
            result = eprint(runner.invoke(cli,["workflow","get-file","-n","namevar"]))
            filename = eprint(runner.invoke(cli,["workflow","get-filename","-n","namevar"]))
            print(filename.output,"all output")
            assert filename.output == "file.json\n"

    def test_get_datapath(self,setup_simple_bucket):            
        runner = CliRunner()
        with runner.isolated_filesystem():
            with pytest.raises(AssertionError):
                result = eprint(runner.invoke(cli,["workflow","get-datapath"]))
            result = eprint(runner.invoke(cli,["workflow","initialize-job","-p", "./"]))
            result = eprint(runner.invoke(cli,["workflow","register-dataset","-b","testinterface","-k","user/file.json"]))
            with pytest.raises(AssertionError):#assert result.output == "file.json"
                datapath = eprint(runner.invoke(cli,["workflow","get-datapath"]))
            result = eprint(runner.invoke(cli,["workflow","get-data"]))
            datapath = eprint(runner.invoke(cli,["workflow","get-datapath"]))
            print(datapath.output,"all output")
            assert datapath.output == os.path.join(os.path.abspath("./"),"inputs","file.json\n")

    def test_get_configpath(self,setup_simple_bucket):            
        runner = CliRunner()
        with runner.isolated_filesystem():
            with pytest.raises(AssertionError):
                result = eprint(runner.invoke(cli,["workflow","get-configpath"]))
            result = eprint(runner.invoke(cli,["workflow","initialize-job","-p", "./"]))
            result = eprint(runner.invoke(cli,["workflow","register-config","-b","testinterface","-k","user/config.json"]))
            with pytest.raises(AssertionError):#assert result.output == "file.json"
                configpath = eprint(runner.invoke(cli,["workflow","get-configpath"]))
            result = eprint(runner.invoke(cli,["workflow","get-config"]))
            configpath = eprint(runner.invoke(cli,["workflow","get-configpath"]))
            print(configpath.output,"all output")
            assert configpath.output == os.path.join(os.path.abspath("./"),"configs","config.json\n")

    def test_get_filepath(self,setup_simple_bucket):            
        runner = CliRunner()
        with runner.isolated_filesystem():
            with pytest.raises(AssertionError):
                result = eprint(runner.invoke(cli,["workflow","get-filepath"]))
            result = eprint(runner.invoke(cli,["workflow","initialize-job","-p", "./"]))
            result = eprint(runner.invoke(cli,["workflow","register-file","-n","namevar","-b","testinterface","-k","user/file.json"]))
            #assert result.output == "file.json"
            result = eprint(runner.invoke(cli,["workflow","get-file","-n","namevar"]))
            filepath = eprint(runner.invoke(cli,["workflow","get-filepath","-n","namevar"]))
            print(filepath.output,"all output")
            assert filepath.output == os.path.join(os.path.abspath("./"),"inputs","file.json\n")

    def test_get_resultpath(self,setup_simple_bucket):            
        bucketname,username,contents,s3_client,s3_resource = setup_simple_bucket
        runner = CliRunner()
        with runner.isolated_filesystem():
            os.mkdir("local")
            os.mkdir("local/dir")
            with open("./local/file.txt","w") as f:
                f.close()
            with pytest.raises(AssertionError):
                result = eprint(runner.invoke(cli,["workflow","get-resultpath","-l","local/file.txt"]))
            result = eprint(runner.invoke(cli,["workflow","initialize-job","-p", "./"]))
            result = eprint(runner.invoke(cli,["workflow","register-resultpath","-b",bucketname,"-k","keypath/"]))
            result = eprint(runner.invoke(cli,["workflow","get-resultpath","-l","local/file.txt"]))
            assert result.output == os.path.join("s3://",bucketname,"keypath","process_results","file.txt\n")
            result = eprint(runner.invoke(cli,["workflow","get-resultpath","-l","local/dir/"]))
            assert result.output == os.path.join("s3://",bucketname,"keypath","process_results","dir\n")

    def test_log_command(self,setup_simple_bucket):       
        runner = CliRunner()
        scriptpath = os.path.join(testdir,"test_mats","sendtime.sh")
        with runner.isolated_filesystem():
            with pytest.raises(AssertionError):
                result = eprint(runner.invoke(cli,["workflow","log-command","-c","echo hi","-b","testinterface","-r","path/to/results"]))
            result = eprint(runner.invoke(cli,["workflow","initialize-job","-p", "./"]))
            with pytest.raises(AssertionError):
                result = eprint(runner.invoke(cli,["workflow","log-command","-c","echo hi","-b","testinterface","-r","path/to/results"]))
            result = eprint(runner.invoke(cli,["workflow","register-dataset","-b","testinterface","-k","user/file.json"]))
            result = eprint(runner.invoke(cli,["workflow","get-data"]))
            result = eprint(runner.invoke(cli,["workflow","log-command","-c",scriptpath,"-b","testinterface","-r","path/to/results"]))
 
            assert os.path.exists(os.path.join("./","logs","log.txt"))

    def test_cleanup(self,setup_simple_bucket):
        bucketname,username,contents,s3_client,s3_resource = setup_simple_bucket
        runner = CliRunner()
        with runner.isolated_filesystem():
            with pytest.raises(AssertionError):
                result = eprint(runner.invoke(cli,["workflow","cleanup"]))
            result = eprint(runner.invoke(cli,["workflow","initialize-job","-p", "./"]))
            with open("./.neurocaas_contrib_storageloc_test.json", "r") as f:
                storage = json.load(f)
            assert storage["path"] == os.path.abspath("./")
            print(os.path.abspath("./"))
            result = eprint(runner.invoke(cli,["workflow","register-config","-b",bucketname,"-k",f"{username}/config.json"]))
            result = eprint(runner.invoke(cli,["workflow","register-resultpath","-b",bucketname,"-k",f"{username}/results/"]))
            result = eprint(runner.invoke(cli,["workflow","cleanup"]))
            config =  s3_client.download_file(bucketname,f"{username}/results/process_results/config.json","./key.txt")
            config =  s3_client.download_file(bucketname,f"{username}/results/process_results/update.txt","./update.txt")

### Test remote instance management.  
def test_develop_remote(setup_log_bucket):
    bucket_name = setup_log_bucket
    runner = CliRunner()
    with runner.isolated_filesystem():
        os.mkdir("./logs")
        result = eprint(runner.invoke(cli,["init","--location","./"],input = "{}\n{}".format(bucket_name,"Y")))
        with open(".neurocaas_contrib_config_test.json") as f:
            configdict = json.load(f)
        assert configdict["develop_dict"] == {}
        #print(configdict)
        #assert 0 
        result = eprint(runner.invoke(cli,["develop-remote"]))
        with open(".neurocaas_contrib_config_test.json") as f:
            configdict_full = json.load(f)
        assert type(configdict_full["develop_dict"]["config"]) == dict

### Test remote instance management when development history exists.  
def test_develop_remote(setup_log_bucket):
    bucket_name = setup_log_bucket
    runner = CliRunner()
    with runner.isolated_filesystem():
        os.mkdir("./logs")
        result = eprint(runner.invoke(cli,["init","--location","./"],input = "{}\n{}".format(bucket_name,"Y")))
        with open(".neurocaas_contrib_config_test.json") as f:
            configdict = json.load(f)
        assert configdict["develop_dict"] == None
        result = eprint(runner.invoke(cli,["develop-remote"]))
        with open(".neurocaas_contrib_config_test.json") as f:
            configdict_full = json.load(f)
        assert type(configdict_full["develop_dict"]["config"]) == dict

def test_develop_remote_existing(setup_log_bucket):
    bucket_name = setup_log_bucket
    runner = CliRunner()
    with runner.isolated_filesystem():
        os.mkdir("./logs")
        result = eprint(runner.invoke(cli,["init","--location","./"],input = "{}\n{}".format(bucket_name,"y")))
        
        shutil.copy(os.path.join(here,"test_mats","stack_config_template.json"),os.path.join("./",bucket_name,"stack_config_template.json"))
        with open(os.path.join("./",bucket_name,"stack_config_template.json")) as f:
            stackconfig = json.load(f)
        with open(".neurocaas_contrib_config_test.json") as f:
            configdict = json.load(f)
        assert configdict["develop_dict"] == None 
        result = eprint(runner.invoke(cli,["develop-remote"],input = "{}".format("y")))
        with open(".neurocaas_contrib_config_test.json") as f:
            configdict_full = json.load(f)
 
        ## assert that the development history saved into the cli tool config file is the same that was recorded in the blueprint. 
        assert type(configdict_full["develop_dict"]) == dict

    assert stackconfig.get("develop_history",[None])[0] == configdict_full["develop_dict"]
    ## This assumes that develop history exists already - replace with the above. We should separately test the case where the config file contains a blueprint in the develop history. 
    #assert stackconfig["develop_history"][0] == configdict_full["develop_dict"]

def test_assign_instance(setup_log_bucket,mock_boto3_for_remote):
    instance,ami = mock_boto3_for_remote
    amiid = "bs"
    bucket_name = setup_log_bucket
    runner = CliRunner()
    with runner.isolated_filesystem():
        os.mkdir("./logs")
        result = eprint(runner.invoke(cli,["init","--location","./"],input = "{}\n{}".format(bucket_name,"y")))
        
        shutil.copy(os.path.join(here,"test_mats","stack_config_template.json"),os.path.join("./",bucket_name,"stack_config_template.json"))
        result = eprint(runner.invoke(cli,["develop-remote"],input = "{}".format("y")))
        eprint(runner.invoke(cli,["assign-instance","--instance",instance.id]))
        with open(".neurocaas_contrib_config_test.json") as f:
            configdict_full = json.load(f)

        assert configdict_full["develop_dict"]["instance_id"] == instance.id

def test_launch_devinstance(setup_log_bucket,mock_boto3_for_remote):
    instance,ami = mock_boto3_for_remote
    bucket_name = setup_log_bucket
    runner = CliRunner()
    with runner.isolated_filesystem():
        os.mkdir("./logs")
        result = eprint(runner.invoke(cli,["init","--location","./"],input = "{}\n{}".format(bucket_name,"y")))
        
        shutil.copy(os.path.join(here,"test_mats","stack_config_template.json"),os.path.join("./",bucket_name,"stack_config_template.json"))
        result = eprint(runner.invoke(cli,["develop-remote"],input = "{}".format("y")))
        eprint(runner.invoke(cli,["launch-devinstance","--amiid",ami]))
        with open(".neurocaas_contrib_config_test.json") as f:
            configdict_full = json.load(f)
        instance = ec2_resource.Instance(configdict_full["develop_dict"]["instance_id"])    
        assert instance.image_id == ami

def test_instance_lifecycle(setup_log_bucket,mock_boto3_for_remote):
    instance,ami = mock_boto3_for_remote
    bucket_name = setup_log_bucket
    runner = CliRunner()
    with runner.isolated_filesystem():
        os.mkdir("./logs")
        result = eprint(runner.invoke(cli,["init","--location","./"],input = "{}\n{}".format(bucket_name,"y")))
        
        shutil.copy(os.path.join(here,"test_mats","stack_config_template.json"),os.path.join("./",bucket_name,"stack_config_template.json"))
        result = eprint(runner.invoke(cli,["develop-remote"],input = "{}".format("y")))
        eprint(runner.invoke(cli,["launch-devinstance","--amiid",ami]))
        eprint(runner.invoke(cli,["stop-devinstance"]))
        eprint(runner.invoke(cli,["start-devinstance"]))
        eprint(runner.invoke(cli,["terminate-devinstance","--force",True]))

def test_instance_lifecycle_assigned(setup_log_bucket,mock_boto3_for_remote):
    instance,ami = mock_boto3_for_remote
    bucket_name = setup_log_bucket
    runner = CliRunner()
    with runner.isolated_filesystem():
        os.mkdir("./logs")
        result = eprint(runner.invoke(cli,["init","--location","./"],input = "{}\n{}".format(bucket_name,"y")))
        
        shutil.copy(os.path.join(here,"test_mats","stack_config_template.json"),os.path.join("./",bucket_name,"stack_config_template.json"))
        result = eprint(runner.invoke(cli,["develop-remote"],input = "{}".format("y")))
        eprint(runner.invoke(cli,["assign-instance","-i",instance.id]))
        eprint(runner.invoke(cli,["stop-devinstance"]))
        eprint(runner.invoke(cli,["start-devinstance"]))
        eprint(runner.invoke(cli,["terminate-devinstance","--force",True]))

def test_submit_job(setup_log_bucket,mock_boto3_for_remote):
    instance,ami = mock_boto3_for_remote
    bucket_name = setup_log_bucket
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("./submit.json","w") as f:
            json.dump({"dataname":os.path.join("bendeskylab","inputs","dummyinput.json"),"configname":os.path.join(bucket_name,"logs","s"),"timestamp":"rr"},f)
        s3_client.upload_file("./submit.json",bucket_name,"bendeskylab/inputs/dummyinput.json")
        os.mkdir("./logs")
        result = eprint(runner.invoke(cli,["init","--location","./"],input = "{}\n{}".format(bucket_name,"y")))
        
        shutil.copy(os.path.join(here,"test_mats","stack_config_template.json"),os.path.join("./",bucket_name,"stack_config_template.json"))
        result = eprint(runner.invoke(cli,["develop-remote"],input = "{}".format("y")))
        eprint(runner.invoke(cli,["assign-instance","-i",instance.id]))
        eprint(runner.invoke(cli,["submit-job", "-s", "./submit.json"]))
        eprint(runner.invoke(cli,["terminate-devinstance","--force",True]))

def test_job_output(setup_log_bucket,mock_boto3_for_remote):
    instance,ami = mock_boto3_for_remote
    bucket_name = setup_log_bucket
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("./submit.json","w") as f:
            json.dump({"dataname":os.path.join("bendeskylab","inputs","dummyinput.json"),"configname":os.path.join(bucket_name,"logs","s"),"timestamp":"rr"},f)
        s3_client.upload_file("./submit.json",bucket_name,"bendeskylab/inputs/dummyinput.json")
        os.mkdir("./logs")
        result = eprint(runner.invoke(cli,["init","--location","./"],input = "{}\n{}".format(bucket_name,"y")))
        
        shutil.copy(os.path.join(here,"test_mats","stack_config_template.json"),os.path.join("./",bucket_name,"stack_config_template.json"))
        result = eprint(runner.invoke(cli,["develop-remote"],input = "{}".format("y")))
        eprint(runner.invoke(cli,["assign-instance","-i",instance.id]))
        eprint(runner.invoke(cli,["submit-job", "-s", "./submit.json"]))
        eprint(runner.invoke(cli,["job-output"]))
        eprint(runner.invoke(cli,["terminate-devinstance","--force",True]))

def test_create_devami(setup_log_bucket,mock_boto3_for_remote):
    instance,ami = mock_boto3_for_remote
    bucket_name = setup_log_bucket
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("./submit.json","w") as f:
            json.dump({"dataname":os.path.join("bendeskylab","inputs","dummyinput.json"),"configname":os.path.join(bucket_name,"logs","s"),"timestamp":"rr"},f)
        s3_client.upload_file("./submit.json",bucket_name,"bendeskylab/inputs/dummyinput.json")
        os.mkdir("./logs")
        result = eprint(runner.invoke(cli,["init","--location","./"],input = "{}\n{}".format(bucket_name,"y")))
        
        shutil.copy(os.path.join(here,"test_mats","stack_config_template.json"),os.path.join("./",bucket_name,"stack_config_template.json"))
        result = eprint(runner.invoke(cli,["develop-remote"],input = "{}".format("y")))
        eprint(runner.invoke(cli,["assign-instance","-i",instance.id]))
        eprint(runner.invoke(cli,["create-devami","-n","falseami"]))
        eprint(runner.invoke(cli,["terminate-devinstance","--force",True]))

def test_update_blueprint(setup_log_bucket,mock_boto3_for_remote):
    instance,ami = mock_boto3_for_remote
    bucket_name = setup_log_bucket
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("./submit.json","w") as f:
            json.dump({"dataname":os.path.join("bendeskylab","inputs","dummyinput.json"),"configname":os.path.join(bucket_name,"logs","s"),"timestamp":"rr"},f)
        s3_client.upload_file("./submit.json",bucket_name,"bendeskylab/inputs/dummyinput.json")
        os.mkdir("./logs")
        result = eprint(runner.invoke(cli,["init","--location","./"],input = "{}\n{}".format(bucket_name,"y")))
        stackconfig = os.path.join(here,"test_mats","stack_config_template.json")
        shutil.copy(stackconfig,os.path.join("./",bucket_name,"stack_config_template.json"))
        subprocess.call(["git","init","./{}".format(bucket_name)])
        os.chdir("./".format(bucket_name))
        subprocess.call(["git","add","stack_config_template.json"])
        subprocess.call(["git","commit","-m","initial commit"])
        with open(stackconfig) as f:
            sc_old = json.load(f)
            ami_old = sc_old["Lambda"]["LambdaConfig"]["AMI"]
        result = eprint(runner.invoke(cli,["develop-remote"],input = "{}".format("y")))
        eprint(runner.invoke(cli,["assign-instance","-i",instance.id]))
        eprint(runner.invoke(cli,["create-devami","-n","falseami"]))
        print(os.getcwd())
        os.chdir("./".format(bucket_name))
        print(os.getcwd())
        eprint(runner.invoke(cli,["update-blueprint"]))
        with open(stackconfig) as f:
            sc_new = json.load(f)
            ami_new = sc_new["Lambda"]["LambdaConfig"]["AMI"]
        eprint(runner.invoke(cli,["terminate-devinstance","--force",True]))
        assert ami_new != ami_old
        ## todo check that the blueprint is correctly updated.

def test_update_history(setup_log_bucket,mock_boto3_for_remote):
    instance,ami = mock_boto3_for_remote
    bucket_name = setup_log_bucket
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("./submit.json","w") as f:
            json.dump({"dataname":os.path.join("bendeskylab","inputs","dummyinput.json"),"configname":os.path.join(bucket_name,"logs","s"),"timestamp":"rr"},f)
        s3_client.upload_file("./submit.json",bucket_name,"bendeskylab/inputs/dummyinput.json")
        os.mkdir("./logs")
        result = eprint(runner.invoke(cli,["init","--location","./"],input = "{}\n{}".format(bucket_name,"y")))
        
        stackconfig = os.path.join("./",bucket_name,"stack_config_template.json")
        shutil.copy(os.path.join(here,"test_mats","stack_config_template.json"),stackconfig)
        with open(stackconfig) as f:
            sc_old = json.load(f)
            hist_old = sc_old["develop_history"]
        result = eprint(runner.invoke(cli,["develop-remote"],input = "{}".format("y")))
        eprint(runner.invoke(cli,["assign-instance","-i",instance.id]))
        eprint(runner.invoke(cli,["create-devami","-n","falseami"]))
        eprint(runner.invoke(cli,["update-history"]))
        eprint(runner.invoke(cli,["terminate-devinstance","--force",True]))
