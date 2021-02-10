import neurocaas_contrib.scripting as scripting
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


