import pytest 
from neurocaas_contrib.local import NeuroCAASAutoScript

scriptdict = "../src/neurocaas_contrib/example_scriptdict.json"
scriptdict_env = "../src/neurocaas_contrib/example_scriptdict_env.json"
template = "../src/neurocaas_contrib/template_script.sh"

class Test_NeuroCAASAutoScript(object):
    def test_NeuroCAASAutoScript(self):
        ncas = NeuroCAASAutoScript(scriptdict,template)

    def test_NeurCAASAutoScript_append_conda_path_command(self):
        ncas = NeuroCAASAutoScript(scriptdict,template)
        ncap.append_conda_path_command()

    def test_NeurCAASAutoScript_append_conda_path_command_custom(self):
        ncas = NeuroCAASAutoScript(scriptdict,template)
        ncap.append_conda_path_command("/Users/taigaabe/anaconda3/bin")
