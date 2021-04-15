import neurocaas_contrib.scripting as scripting
import shlex
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
