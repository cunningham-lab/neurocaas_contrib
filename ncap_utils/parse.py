import re 
import sys

var = sys.argv[1]


try:
    print(re.findall('.+/inputs',var)[0])
except:
    raise NotImplementedError(var)
