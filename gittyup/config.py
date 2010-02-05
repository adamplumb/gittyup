#
# config.py
#

import os
from _configobj.configobj import ConfigObj

def get_local_config_path(repository_path):
    return repository_path + "/.git/config"

def get_global_config_path():
    return os.path.expanduser("~/.gitconfig")

def get_system_config_path():
    return "/etc/gitconfig"

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

    def has(self, section, key=None):
        if section in self._config:
            if key is None:
                return True
            else:
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

class GittyupLocalConfig(GittyupConfig):
    def __init__(self, repository_path):
        GittyupConfig.__init__(self, get_local_config_path(repository_path))
        
class GittyupGlobalConfig(GittyupConfig):
    def __init__(self):
        GittyupConfig.__init__(self, get_global_config_path())

class GittyupSystemConfig(GittyupConfig):
    def __init__(self):
        GittyupConfig.__init__(self, get_system_config_path())

class GittyupFallbackConfig:
    def set(self, section, key, value):
        self._config(section, key).set(section, key, value)
    
    def get(self, section, key):
        return self._config(section, key).get(section, key)
    
    def has(self, section, key=None):
        return self._config(section, key).has(section, key)
    
    def rename(self, section, old_key, new_key):
        self._config(section, old_key).rename(section, old_key, new_key)
    
    def get_all(self):
        return self._config(section, key).get_all()
    
    def set_section(self, section, items):
        self._config(section).set_section(section, items)

    def get_section(self, section):
        return self._config(section).get_section(section)
    
    def rename_section(self, old_section, new_section):
        self._config(old_section).rename_section(old_section, new_section)
    
    def remove_section(self, section):
        self._config(section).remove_section(section)

    def get_inline_comment(self, section, key):
        return self._config(section, key).get_inline_comment(section, key)
    
    def set_inline_comment(self, section, key, value):
        self._config(section, key).set_inline_comment(section, key, value)
    
    def remove_inline_comment(self, section, key):
        self._config(section, key).remove_inline_comment(section, key)

    def get_comment(self, section, key):
        return self._config(section, key).get_comment(section, key)
    
    def set_comment(self, section, key, value):
        self._config(section, key).set_comment(section, key, value)
    
    def remove_comment(self, section, key):
        self._config(section, key).remove_comment(section, key)

    def _config(self, section, key=None):
        raise NotImplementedError()

    def _write(self):
        raise NotImplementedError()

class GittyupLocalFallbackConfig(GittyupFallbackConfig):
    def __init__(self, repository_path):
        self._local = GittyupLocalConfig(repository_path)
        self._global = GittyupGlobalConfig()
        self._system = GittyupSystemConfig()

    def _config(self, section, key=None):
        if self._global.has(section, key):
            config = self._global
        elif self._system.has(section, key):
            config = self._system
        else:
            config = self._local
                
        return config

    def write(self):
        self._local.write()
        self._global.write()
        
        # Only root can write to the system config file
        if os.getcwd() == 0:
            self._system.write()

class GittyupGlobalFallbackConfig(GittyupFallbackConfig):
    def __init__(self):
        self._global = GittyupGlobalConfig()
        self._system = GittyupSystemConfig()

    def _config(self, section, key=None):
        if self._global.has(section, key):
            config = self._global
        elif self._system.has(section, key):
            config = self._system
                
        return config

    def write(self):
        self._global.write()

        # Only root can write to the system config file
        if os.getcwd() == 0:
            self._system.write()
