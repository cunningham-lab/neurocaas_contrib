import pytest
from pathlib import Path
import traceback
import docker
from click.testing import CliRunner
from neurocaas_contrib.cli_commands import *
from neurocaas_contrib.local import default_neurocaas_repo

docker_client = docker.from_env()

containername = "neurocaasdevcontainer"
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

def test_cli_setup_development_container(remove_container):
    runner = CliRunner()
    name = "setupimage"
    imagename = "neurocaas/test:base"

    with runner.isolated_filesystem():
        result = eprint(runner.invoke(cli,["init","--location","./"],input ="{}\n{}".format(name,"Y")))
        assert os.path.exists("./"+name+"/stack_config_template.json") == True
        result = eprint(runner.invoke(cli,["setup-development-container"]))
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
        result = eprint(runner.invoke(cli,["setup-development-container","--image",imagename,"--container",namedcontainername]))
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
        result = eprint(runner.invoke(cli,["setup-development-container","--image",imagerepo,"--container",namedcontainername]))
        result = eprint(runner.invoke(cli,["save-developed-image","--tagid",testid,"--force","--container",namedcontainername]))
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
        result = eprint(runner.invoke(cli,["setup-inputs","-d",datapath,"-d",datapath2,"-c",confpath]))
        assert os.path.exists(os.path.join("setupinputs","io-dir","inputs","data.txt"))
        assert os.path.exists(os.path.join("setupinputs","io-dir","inputs","data2.txt"))
        assert os.path.exists(os.path.join("setupinputs","io-dir","configs","config.json"))
        with open("./"+name+"/stack_config_template.json") as f: 
            blueprint = json.load(f)
    assert blueprint["localenv"] == "./setupinputs"      

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
        result = eprint(runner.invoke(cli,["setup-inputs","-d",datapath,"-d",datapath2,"-c",confpath]))
        assert os.path.exists("./"+name+"/stack_config_template.json") == True
        result = eprint(runner.invoke(cli,["setup-development-container","--image",imagename,"--container",namedcontainername]))
        with open("./"+name+"/stack_config_template.json") as f: 
            blueprint = json.load(f)
    assert blueprint["container_history"][-1] == namedcontainername
    assert blueprint["image_history"][-1] == imagename 
