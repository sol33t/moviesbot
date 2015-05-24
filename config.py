"""
Reads config.yaml for config values
Sets the config values as attributes to this function

To get a config value from another module, do:

import config
value = config.key
"""

import yaml
import sys

thismodule = sys.modules[__name__]
with open("config.yaml", 'r') as ymlfile:
    for key,value in yaml.load(ymlfile).iteritems():
        setattr(thismodule, key, value)