## module for scripting tools. 
import yaml
import json

def get_yaml_field(yamlfile,fieldname):
    """returns the value of a field in a yaml file. 

    :param yamlfile: path to the yaml file you want to parse. 
    :param fieldname: the name of the field you want to extract. 
    """
    with open(yamlfile,"r") as f:
        ydict = yaml.full_load(f)
    try:    
        output = ydict[fieldname]
    except KeyError:    
        raise KeyError("No field {} exists in this yaml file.".format(fieldname))
    ftype = type(output)
    if ftype is not dict:
        return str(output)
    else:
        return json.dumps(output)


