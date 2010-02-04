#
# client.py
#

import os

from time import time

from dulwich import errors
from dulwich.repo import Repo
from dulwich.objects import Blob, Tree, Commit, Tag, parse_timezone
from dulwich.index import commit_index, SHA1Writer, write_index_dict
from dulwich.errors import NotGitRepository

from cobragit.exceptions import *
from cobragit.util import relativepath, splitall
from cobragit.objects import *

AUTHOR = "Adam Plumb <adamplumb@gmail.com>"
TZ = parse_timezone("-500")
ENCODING = "UTF-8"

DULWICH_COMMIT_TYPE = 1
DULWICH_TREE_TYPE = 2
DULWICH_BLOB_TYPE = 3
DULWICH_TAG_TYPE = 4

class CobraGitClient:
    def __init__(self, path=None):        
        if path:
            try:
                self.repo = Repo(os.path.realpath(path))
            except NotGitRepository:
                raise CobraGitNotRepository()
        else:
            self.repo = None

    ### Start Private Methods ###

    def _initialize_index(self):
        index_path = self.repo.index_path()
        f = open(index_path, "wb")
        try:
            f = SHA1Writer(f)
            write_index_dict(f, {})
        finally:
            f.close()

    def _get_index(self):
        if self.repo.has_index() == False:
            self._initialize_index()
        
        return self.repo.open_index()
    
    def _get_tree_at_head(self):
        try:
            tree = self.repo.tree(self.repo.commit(self.repo.head()).tree)
        except KeyError, e:
            tree = Tree()

        return tree

    def _get_working_tree(self):
        return self.repo.tree(commit_index(self.repo.object_store, self._get_index()))
    
    def _read_directory_tree(self, path):
        paths = []
        for root, dirs, filenames in os.walk(path, topdown=True):
            try:
                dirs.remove(".git")
            except ValueError:
                pass

            for filename in filenames:
                paths.append(self._get_relative_path(os.path.join(root, filename)))
        
        return sorted(paths)

    def _get_repository_path(self, path):
        path_to_check = os.path.realpath(path)
        while path_to_check != "/" and path_to_check != "":
            if os.path.isdir(os.path.join(path_to_check, ".git")):
                return path_to_check
            
            path_to_check = os.path.split(path_to_check)[0]
        
        return None

    def _get_relative_path(self, path):
        return relativepath(os.path.realpath(self.repo.path), path)            

    def _get_blob_from_file(self, path):
        file = open(path, "rb")
        try:
            blob = Blob.from_string(file.read())
        finally:
            file.close()
        
        return blob

    def _write_blob_to_file(self, path, blob):
        file = open(path, "wb")
        try:
            file.write(blob.get_data())
        finally:
            file.close()

    ### Start Public Methods ###

    def initialize_repository(self, path):
        if not os.path.exists(path):
            os.mkdir(path)
        self.repo = Repo.init(path)

    def set_repository(self, path):
        try:
            self.repo = Repo(os.path.realpath(path))
        except NotGitRepository:
            raise CobraGitNotRepository()
    
    def stage(self, path):
        print "git.stage %s" % path

        tree = self._get_tree_at_head()
        relative_path = self._get_relative_path(path)
        blob = self._get_blob_from_file(relative_path)
        
        (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(relative_path)
        index = self._get_index()
        index[relative_path] = (ctime, mtime, dev, ino, mode, uid, gid, size, blob.id, 0)
        index.write()

        self.repo.object_store.add_object(blob)
    
    def stage_all_changed(self):
        print "git.stage_all"

        index = self._get_index()
        for status in self.status():
            if status.identifier in ["added", "removed", "modified"]:
                self.stage(status.path)

            if status.identifier == "missing":
                del index[status.path]
                index.write()           

    def unstage(self, path):
        print "git.unstage %s" % path

        index = self._get_index()
        relative_path = self._get_relative_path(path)

        if relative_path in index:
            tree = self._get_tree_at_head()
            if relative_path in tree:
                (ctime, mtime, dev, ino, mode, uid, gid, size, blob_id, flags) = index[relative_path]
                (mode, blob_id) = tree[relative_path]
                index[relative_path] = (ctime, mtime, dev, ino, mode, uid, gid, size, blob_id, flags)
            else:
                del index[relative_path]

            index.write()
    
    def checkout(self, paths=[], tree_sha=None, commit_sha=None):
        print "git.checkout"

        tree = None
        if tree_sha:
            try:
                tree = self.repo.tree(tree_sha)
            except AssertionError:
                raise CobraGitNotTree(tree_sha)
        elif commit_sha:
            try:
                commit = self.repo.commit(commit_sha)
                tree = commit.tree
            except AssertionError:
                raise CobraGitNotCommit(commit_sha)

        if not tree:
            tree = self._get_tree_at_head()

        relative_paths = []
        for path in paths:
            relative_paths = self._get_relative_path(path)

        for (name, mode, sha) in self.repo.object_store.iter_tree_contents(tree.id):
            if name in relative_paths or len(paths) == 0:
                self._write_blob_to_file(name, self.repo.get_blob(sha))
    
    def commit(self, message, commit_all=False):
        print "git.commit"

        if commit_all:
            self.stage_all_changed()

        commit = Commit()
        initial_commit = False
        try:
            commit.parents = [self.repo.head()]
        except KeyError:
            # The initial commit has no parent
            initial_commit = True
            pass
        
        commit.tree = commit_index(self.repo.object_store, self._get_index())
        commit.message = message
        commit.author = commit.committer = AUTHOR
        commit.commit_time = commit.author_time = int(time())
        commit.commit_timezone = commit.author_timezone = TZ
        commit.encoding = ENCODING
        
        self.repo.object_store.add_object(commit)
        
        self.repo.refs["refs/heads/master"] = commit.id
        
        if initial_commit:
            self.repo.refs["HEAD"] = "ref: refs/heads/master"
    
    def tag(self, name, message):
        print "git.tag",name

        tag = Tag()
        
        tag.name = name
        tag.tagger = AUTHOR
        tag.tag_time = int(time())
        tag.tag_timezone = TZ
        tag.message = message
        tag.set_object((DULWICH_COMMIT_TYPE, self.repo.head()))

        self.repo.object_store.add_object(tag)
        
        self.repo.refs["refs/tags/%s" % name] = tag.id
    
    def tag_delete(self, name):
        print "git.tag_delete %s" % name

        ref_name = "refs/tags/%s" % name
        refs = self.repo.get_refs()
        if ref_name in refs:
            del self.repo.refs[ref_name]
    
    def tags_list(self):
        print "git.tags_list"
        
        refs = self.repo.get_refs()
        tags = []
        for ref,tag_sha in refs.items():
            if ref.startswith("refs/tags"):
                tag = CobraGitTag(tag_sha, self.repo[tag_sha])
                tags.append(tag)
        
        return tags
    
    def status(self):
        print "git.status"
        
        tree_at_head = self._get_tree_at_head()
        index = self._get_index()
        paths = self._read_directory_tree(self.repo.path)
        
        statuses = []

        tracked_paths = set(index)
        for (name, mode, sha) in self.repo.object_store.iter_tree_contents(tree_at_head.id):
            if os.path.exists(name):
                if name in tracked_paths:
                    # Cached, determine if modified or not
                    tracked_paths.remove(name)
                    
                    blob = self._get_blob_from_file(name)
                    if blob.id == index[name][8]:
                        statuses.append(CobraGitNormalStatus(name))
                    else:
                        statuses.append(CobraGitModifiedStatus(name))
                else:
                    # Removed
                    statuses.append(CobraGitRemovedStatus(name))
            else:
                # Missing
                tracked_paths.remove(name)
                statuses.append(CobraGitMissingStatus(name))

            try:
                paths.remove(name)
            except ValueError:
                pass

        for name in tracked_paths:
            # Added
            statuses.append(CobraGitAddedStatus(name))
            try:
                paths.remove(name)
            except ValueError:
                pass

        # Find untrackedfiles
        for path in paths:
            statuses.append(CobraGitUntrackedStatus(path))

        return statuses
