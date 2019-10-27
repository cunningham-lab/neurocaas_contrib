import re 
import sys

var = sys.argv[1]


print(re.findall('.+/inputs',var)[0])
