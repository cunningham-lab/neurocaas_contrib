import pytest 
from neurocaas_contrib.local import NeuroCAASAutoScript
from testpaths import get_dict_file 
import os

filepath = os.path.realpath(__file__)
testpath = os.path.dirname(filepath)
rootpath = os.path.dirname(testpath)

if get_dict_file() == "local":
    scriptdict = os.path.join(rootpath,"src/neurocaas_contrib/example_scriptdict.json")
    scriptdict_env = os.path.join(rootpath,"src/neurocaas_contrib/example_scriptdict_env.json")
elif get_dict_file() == "ci":
    scriptdict = os.path.join(rootpath,"src/neurocaas_contrib/example_scriptdict_travis.json")
    scriptdict_env = os.path.join(rootpath,"src/neurocaas_contrib/example_scriptdict_travis_env.json")
else:
    assert 0,"Home directory not recognized for running tests."
    
template = os.path.join(rootpath,"src/neurocaas_contrib/template_script.sh")
path = "/Users/taigaabe/anaconda3/bin"

class Test_NeuroCAASAutoScript(object):
    def test_NeuroCAASAutoScript(self):
        ncas = NeuroCAASAutoScript(scriptdict,template)

    def test_NeuroCAASAutoScript_add_dlami(self):
        ncas = NeuroCAASAutoScript(scriptdict_env,template)
        ncas.add_dlami()
        ncas.scriptlines[-1] == "source .dlamirc"

    def test_NeuroCAASAutoScript_append_conda_path_command(self):
        ncas = NeuroCAASAutoScript(scriptdict,template)
        command = ncas.append_conda_path_command()
        assert command == f"export PATH=\"{path}:$PATH\""

    def test_NeuroCAASAutoScript_append_conda_path_command_custom(self):
        ncas = NeuroCAASAutoScript(scriptdict,template)
        command = ncas.append_conda_path_command("/Users/taigaabe/anaconda3/bin")
        assert command == f"export PATH=\"{path}:$PATH\""

    def test_NeuroCAASAutoScript_check_conda_env(self):
        ncas = NeuroCAASAutoScript(scriptdict,template)
        assert ncas.check_conda_env("neurocaas")

    def test_NeuroCAASAutoScript_add_conda_env(self):
        ncas = NeuroCAASAutoScript(scriptdict_env,template)
        ncas.add_conda_env()
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

        



