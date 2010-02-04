#
# exceptions.py
#

class CobraGitNotRepository(Exception):
    """Indicates that no Git repository was found."""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class CobraGitNotTree(Exception):
    """Indicates the given sha1 hash does not point to a valid Tree"""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class CobraGitNotCommit(Exception):
    """Indicates the given sha1 hash does not point to a valid Commit"""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class CobraGitNotBlob(Exception):
    """Indicates the given sha1 hash does not point to a valid Blob"""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class CobraGitNotTag(Exception):
    """Indicates the given sha1 hash does not point to a valid Commit"""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)
