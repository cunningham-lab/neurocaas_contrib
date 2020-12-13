import pytest 
import pdb
from neurocaas_contrib.local import NeuroCAASAutoScript,NeuroCAASImage,NeuroCAASLocalEnv
from neurocaas_contrib.log import NeuroCAASDataStatus,NeuroCAASCertificate
from testpaths import get_dict_file 
import docker
import os

filepath = os.path.realpath(__file__)
testpath = os.path.dirname(filepath)
rootpath = os.path.dirname(testpath)

certpath = "s3://caiman-ncap-web/reviewers/results/job__caiman-ncap-web_1589650394/logs/certificate.txt"

if get_dict_file() == "local":
    scriptdict = os.path.join(rootpath,"src/neurocaas_contrib/template_mats/example_scriptdict.json")
    scriptdict_env = os.path.join(rootpath,"src/neurocaas_contrib/template_mats/example_scriptdict_env.json")
    path = "/Users/taigaabe/anaconda3/bin"
elif get_dict_file() == "ci":
    scriptdict = os.path.join(rootpath,"src/neurocaas_contrib/template_mats/example_scriptdict_travis.json")
    scriptdict_env = os.path.join(rootpath,"src/neurocaas_contrib/template_mats/example_scriptdict_travis_env.json")
    path = "/home/travis/miniconda/bin"
else:
    assert 0,"Home directory not recognized for running tests."
    
client = docker.from_env()


template = os.path.join(rootpath,"src/neurocaas_contrib/template_script.sh")

class Test_NeuroCAASImage(object):
    def test_NeuroCAASImage(self):
        nci = NeuroCAASImage()
    def test_NeuroCAASImage_assign_default_image(self):
        nci = NeuroCAASImage()
        image_tag = "hello-world:latest"
        nci.assign_default_image(image_tag)
        assert nci.image_tag == image_tag 
        assert nci.image == client.images.get(image_tag)
    def test_NeuroCAASImage_assign_default_image_noimage(self):
        nci = NeuroCAASImage()
        image_tag = "neurocaas/contrib"
        with pytest.raises(AssertionError):
            nci.assign_default_image(image_tag)
    def test_NeuroCAASImage_assign_default_container(self):
        nci = NeuroCAASImage()
        container = client.containers.create("hello-world:latest")
        cname = container.name
        nci.assign_default_container(cname)
        assert nci.container_name == cname
        assert nci.current_container == container
    def test_NeuroCAASImage_assign_default_container_exists(self):
        nci = NeuroCAASImage()
        container1 = client.containers.create("hello-world:latest")
        cname1 = container1.name
        container2 = client.containers.create("hello-world:latest")
        cname2 = container2.name
        nci.assign_default_container(cname1)
        nci.assign_default_container(cname2)
        assert nci.container_name == cname2
        assert nci.current_container == container2
        assert nci.container_history[container1.id] == container1
    def test_NeuroCAASImage_assign_default_container_noexists(self):
        nci = NeuroCAASImage()
        with pytest.raises(docker.errors.NotFound):
            nci.assign_default_container("trash")
    def test_NeuroCAASImage_find_image(self):
        nci = NeuroCAASImage()
        nci.find_image("hello-world:latest")
    def test_NeuroCAASImage_find_image_noimage(self):
        nci = NeuroCAASImage()
        with pytest.raises(AssertionError):
            nci.find_image("neurocaas/contrib")
    def test_NeuroCAASImage_build_default_image(self):
        nci = NeuroCAASImage()
        nci.build_default_image()
    def test_NeuroCAASImage_setup_container(self):
        nci = NeuroCAASImage()
        nci.setup_container()
        try:
            container = nci.client.containers.get("neurocaasdevcontainer")
            container.remove(force=True)
        except:    
            pass
    def test_NeuroCAASImage_test_container(self):
        """This test can be a lot more sensitive and specific. This is just a basic test that the program finishes. 

        """
        nci = NeuroCAASImage()
        containername = "test_container"
        nci.setup_container(container_name=containername)
        nci.test_container(command='ls')
        try:
            container = nci.client.containers.get(containername)
            container.remove(force=True)
        except:    
            pass
    def test_NeuroCAASImage_test_container_stopped(self):
        """This test can be a lot more sensitive and specific. This is just a basic test that the program finishes. 

        """
        nci = NeuroCAASImage()
        container = client.containers.create("hello-world:latest")
        cname = container.name
        nci.assign_default_container(cname)
        with pytest.raises(docker.errors.APIError):
            nci.test_container(command='ls')
        try:
            container = nci.client.containers.get(containername)
            container.remove(force=True)
        except:    
            pass

    def test_NeuroCAASImage_write_logs(self): 
        logpath = "./test_mats/test_analysis/"
        #testgen = (a for a in ["0".encode("utf-8"),"1".encode("utf-8"),"2".encode("utf-8"),"3".encode("utf-8"),"4".encode("utf-8")])
        nci = NeuroCAASImage()
        ncle = NeuroCAASLocalEnv("./test_mats")
        container = client.containers.run(image = nci.image_tag,command = "ls",detach = True)
        datastatus = NeuroCAASDataStatus("s3://dummy_path",container)
        certificate = NeuroCAASCertificate("s3://dummy_path")
        nci.write_logs(logpath,datastatus,certificate)

    def test_NeuroCAASImage_run_analysis(self):
        nci = NeuroCAASImage()
        ncle = NeuroCAASLocalEnv("./test_mats")
        nci.run_analysis("ls",ncle)


    def setup_method(self,test_method):
        pass
    def teardown_method(self,test_method):
        client.containers.prune()

class Test_NeuroCAASLocalEnv(object):
    def test_NeuroCAASLocalEnv(self):
        ncle = NeuroCAASLocalEnv("./test_mats")

class Test_NeuroCAASAutoScript(object):
    def test_NeuroCAASAutoScript(self):
        ncas = NeuroCAASAutoScript(scriptdict,template)

    def test_NeuroCAASAutoScript_add_dlami(self):
        ncas = NeuroCAASAutoScript(scriptdict_env,template)
        ncas.add_dlami()
        ncas.scriptlines[-1] == "source .dlamirc"

    def test_NeuroCAASAutoScript_append_conda_path_command(self):
        ncas = NeuroCAASAutoScript(scriptdict,template)
        command = ncas.append_conda_path_command(path)
        assert command == f"export PATH=\"{path}:$PATH\""

    def test_NeuroCAASAutoScript_check_conda_env(self):
        ncas = NeuroCAASAutoScript(scriptdict,template)
        assert ncas.check_conda_env("neurocaas")

    def test_NeuroCAASAutoScript_add_conda_env(self):
        ncas = NeuroCAASAutoScript(scriptdict_env,template)
        ncas.add_conda_env(path = path)
        assert ncas.scriptlines[-2] == f"export PATH=\"{path}:$PATH\" \n" 
        assert ncas.scriptlines[-1] == f"conda activate neurocaas \n"

    def test_NeuroCAASAutoScript_write_new_script(self):
        ncas = NeuroCAASAutoScript(scriptdict,template)
        script_path = os.path.join(testpath,"test_mats/test_write_new_script.sh")
        ncas.write_new_script(script_path)
        with open(script_path,"r") as f1:
            with open(template,"r") as f2:
                f1r = f1.readlines()
                f2r = f2.readlines()
                assert len(f1r) == len(f2r)
                for r1,r2 in zip(f1r,f2r):
                    assert r1 == r2

    def test_NeuroCAASAutoScript_check_dirs(self):
        ncas = NeuroCAASAutoScript(scriptdict,template)
        ncas.check_dirs()
        refpaths = ["mkdir -p \"/home/ubuntu/datastore/\"", "mkdir -p \"/home/ubuntu/outstore/results/\""]

        for s in ncas.scriptlines[-2:]:
            assert s in refpaths


