import os

def get_dict_file():
    homedir = os.environ["HOME"]
    if homedir == "/Users/taigaabe":
        scriptflag = "local"
    else:
        scriptflag = "ci"
    return scriptflag

