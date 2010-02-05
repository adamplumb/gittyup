#
# exceptions.py
#

class GittyupNotRepository(Exception):
    """Indicates that no Git repository was found."""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class GittyupNotTree(Exception):
    """Indicates the given sha1 hash does not point to a valid Tree"""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class GittyupNotCommit(Exception):
    """Indicates the given sha1 hash does not point to a valid Commit"""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class GittyupNotBlob(Exception):
    """Indicates the given sha1 hash does not point to a valid Blob"""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class GittyupNotTag(Exception):
    """Indicates the given sha1 hash does not point to a valid Commit"""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)
