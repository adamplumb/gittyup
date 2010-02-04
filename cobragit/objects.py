#
# objects.py
#

class CobraGitStatus:
    path = None
    def __init__(self, path):
        self.path = path

    def __repr__(self):
        return "<CobraGitStatus %s %s>" % (self.path, self.identifier)

    def __eq__(self, other):
        return (self.identifier == other.identifier)

class CobraGitNormalStatus(CobraGitStatus):
    identifier = "normal"

class CobraGitAddedStatus(CobraGitStatus):
    identifier = "added"

class CobraGitRenamedStatus(CobraGitStatus):
    identifier = "renamed"

class CobraGitRemovedStatus(CobraGitStatus):
    identifier = "removed"

class CobraGitModifiedStatus(CobraGitStatus):
    identifier = "modified"

class CobraGitKilledStatus(CobraGitStatus):
    identifier = "killed"    

class CobraGitUntrackedStatus(CobraGitStatus):
    identifier = "untracked"

class CobraGitMissingStatus(CobraGitStatus):
    identifier = "missing"



class CobraGitObject:
    def __init__(self, sha, obj):
        self.sha = sha
        self.obj = obj

class CobraGitCommit(CobraGitObject):
    def __repr__(self):
        return "<CobraGitCommit %s>" % self.sha

    @property
    def parents(self):
        return self.obj.parents

    @property
    def author(self):
        return self.obj.author

    @property
    def committer(self):
        return self.obj.committer

    @property
    def message(self):
        return self.obj.message

    @property
    def commit_time(self):
        return self.obj.commit_time

    @property
    def commit_timezone(self):
        return self.obj.commit_timezone

    @property
    def author_time(self):
        return self.obj.author_time

    @property
    def author_timezone(self):
        return self.obj.author_timezone

    @property
    def encoding(self):
        return self.obj.encoding

class CobraGitTag(CobraGitObject):
    def __repr__(self):
        return "<CobraGitTag %s>" % self.name

    @property
    def name(self):
        return self.obj.name

    @property
    def tag_type(self):
        return self.obj.type

    @property
    def message(self):
        return self.obj.message
    
    @property
    def tagger(self):
        return self.obj.tagger

    @property
    def tag_time(self):
        return self.obj.tag_time
    
    @property
    def tag_timezone(self):
        return self.obj.tag_timezone

class CobraGitTree(CobraGitObject):
    def __repr__(self):
        return "<CobraGitTree %s>" % self.sha

class CobraGitBranch(CobraGitCommit):
    def __init__(self, name, sha, obj):
        self.name = name
        self.sha = sha
        self.obj = obj

    def __repr__(self):
        return "<CobraGitBranch %s %s>" % (self.name, self.sha)

    @property
    def name(self):
        return self.obj.name
    
    def __eq__(self, other):
        return (self.name == other)
