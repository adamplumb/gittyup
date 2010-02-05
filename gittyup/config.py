#
# config.py
#

import re
import string

class GittyupConfig:
    config = {}
    
    def __init__(self, path):
        self.path = path
        self._read_config()
        
    def _read_config(self):
        f = open(self.path, "r")
        try:
            config_text = f.read()
        finally:
            f.close()

        self._parse_config(config_text)
    
    def _write_config(self):
        config_text = ""
        for section_name, items in self.config.items():
            config_text += "[%s]\n" % section_name
            for key, value in items.items():
                config_text += "\t%s = %s\n" % (key, value)
        
        f = open(self.path, "w")
        try:
            f.write(config_text)
        finally:
            f.close()
    
    def _parse_config(self, config_text):
        self.config = {}
        for line in config_text.split("\n"):
            section = re.match("^\[(.*?)\]$", line)
            item = re.match("^\t(.*?)\s\=\s(.*?)$", line)
            if section:
                current_section = section.group(1)
                self.config[current_section] = {}
            elif item:
                val = item.group(2)
                if val in string.digits:
                    val = int(val)
                elif val in ("true", "false"):
                    val = bool(val)
                    
                self.config[current_section][item.group(1)] = val
    
    def set(self, section, key, value):
        if section not in self.config:
            self.config[section] = {}
            
        self.config[section][key] = value
    
    def get(self, section, key):
        return self.config[section][key]

    def get_all(self):
        return self.config
    
    def set_section(self, section, items):
        self.config[section] = items

    def get_section(self, section):
        return self.config[section]
    
    def rename_section(self, old_section, new_section):
        self.config[new_section] = self.config[old_section]
        del self.config[old_section]
    
    def remove_section(self, section):
        del self.config[section]
        
    def write(self):
        self._write_config()
