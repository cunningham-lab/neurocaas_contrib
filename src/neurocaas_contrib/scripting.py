## module for scripting tools. 
import os
import yaml
import json
import zipfile

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

def parse_zipfile(zipname,path = None): 
    """Given a zipfile, confirms that it is a zipfile, and that it contains one top level directory. Unzips the zip file, and returns the name of the top level directory. Will throw an error if 1) the file path is not a zip file, or 2) if it contains more than one top level directory. 

    """
    assert zipfile.is_zipfile(zipname), "File is not a recognized zip archive"
    archive = zipfile.ZipFile(zipname)
    full_namelist = archive.namelist()
    folder = {item.split("/")[0] for item in full_namelist}.difference({'__MACOSX'})
    filtered_namelist = [fn for fn in full_namelist if not fn.startswith('__MACOSX')]
    assert len(folder) == 1; "Folder must contain only one top level directory." 
    if path is None:
        path = os.path.dirname(zipname)
    archive.extractall(path = path,members = filtered_namelist)
    return folder.pop()

