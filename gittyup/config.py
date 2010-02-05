#
# config.py
#

from _configobj.configobj import ConfigObj

class GittyupConfig:
    def __init__(self, path):
        self.path = path
        self._config = ConfigObj(path, indent_type="\t")
    
    def set(self, section, key, value):
        if section not in self._config:
            self._config[section] = {}
            
        self._config[section][key] = value
    
    def get(self, section, key):
        return self._config[section][key]

    def has(self, section, key):
        return (key in self._config[section])

    def rename(self, section, old_key, new_key):
        self._config[section][new_key] = self._config[section][old_key]
        del self._config[section][old_key]

    def get_all(self):
        return self._config.items()
    
    def set_section(self, section, items):
        self._config[section] = items

    def get_section(self, section):
        return self._config[section]

    def has_section(self, section):
        return (section in self._config)
    
    def rename_section(self, old_section, new_section):
        self._config[new_section] = self._config[old_section]
        del self._config[old_section]
    
    def remove_section(self, section):
        del self._config[section]

    def get_inline_comment(self, section, key):
        if key is not None:
            return self._config[section].inline_comments[key]
        else:
            return self._config.inline_comments[section]
    
    def set_inline_comment(self, section, key, value):
        if section not in self._config.inline_comments:
            self._config.inline_comments[section] = {}
        
        if key is not None:
            self._config[section].inline_comments[key] = value
        else:
            self._config.inline_comments[section] = value
    
    def remove_inline_comment(self, section, key):
        if key is not None:
            del self._config[section].inline_comments[key]
        else:
            self._config.inline_comments[section]

    def get_comment(self, section, key):
        if key is not None:
            return self._config[section].comments[key]
        else:
            return self._config.comments[section]
    
    def set_comment(self, section, key, value):
        if section not in self._config.comments:
            self._config[section].comments = {}
        
        if key is not None:
            self._config[section].comments[key] = value
        else:
            self._config.comments[section] = value
    
    def remove_comment(self, section, key):
        if key is not None:
            del self._config[section].comments[key]
        else:
            del self._config.comments[section]
        
    def write(self):
        self._config.write()
