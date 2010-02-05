#
# client.py
#

import os
from time import time, timezone

import dulwich.errors
import dulwich.repo
import dulwich.objects
from dulwich.index import commit_index, write_index_dict, SHA1Writer

from gittyup.exceptions import *
from gittyup.util import relativepath, splitall
from gittyup.objects import *
from gittyup.config import GittyupLocalFallbackConfig

TZ = -1 * timezone
ENCODING = "UTF-8"

DULWICH_COMMIT_TYPE = 1
DULWICH_TREE_TYPE = 2
DULWICH_BLOB_TYPE = 3
DULWICH_TAG_TYPE = 4

class GittyupClient:
    def __init__(self, path=None, create=False):        
        if path:
            try:
                self.repo = dulwich.repo.Repo(os.path.realpath(path))
                self._load_config()
            except dulwich.errors.NotGitRepository:
                if create:
                    self.repo = self.initialize_repository(path)
                else:
                    raise NotRepositoryError()
        else:
            self.repo = None

    #
    # Start Private Methods
    #

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
            tree = dulwich.objects.Tree()

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
    
    def _get_absolute_path(self, path):
        return os.path.join(self.repo.path, path)      

    def _get_blob_from_file(self, path):
        file = open(path, "rb")
        try:
            blob = dulwich.objects.Blob.from_string(file.read())
        finally:
            file.close()
        
        return blob

    def _write_blob_to_file(self, path, blob):
        file = open(path, "wb")
        try:
            file.write(blob.get_data())
        finally:
            file.close()

    def _load_config(self):
        self.config = GittyupLocalFallbackConfig(self.repo.path)

    def _get_config_user(self):
        try:
            config_user_name = self.config.get("user", "name")
            config_user_email = self.config.get("user", "email")
            return "%s <%s>" % (config_user_name, config_user_email)
        except KeyError:
            return None
        
    #
    # Start Public Methods
    #
    
    def initialize_repository(self, path):
        if not os.path.exists(path):
            os.mkdir(path)
        self.repo = dulwich.repo.Repo.init(path)
        self._load_config()

    def set_repository(self, path):
        try:
            self.repo = dulwich.repo.Repo(os.path.realpath(path))
            self._load_config()
        except dulwich.errors.NotGitRepository:
            raise NotRepositoryError()

    def track(self, name):
        self.repo.refs["HEAD"] = "ref: %s" % name

    def is_tracking(self, name):
        return (self.repo.refs["HEAD"] == "ref: %s" % name)

    def tracking(self):
        return self.repo.refs["HEAD"][5:]
    
    def stage(self, paths):
        tree = self._get_tree_at_head()
        index = self._get_index()
        
        if isinstance(paths, str):
            paths = [paths]

        for path in paths:
            relative_path = self._get_relative_path(path)
            absolute_path = self._get_absolute_path(path)
            blob = self._get_blob_from_file(path)
            
            if relative_path in index:
                (ctime, mtime, dev, ino, mode, uid, gid, size, blob_id, flags) = index[relative_path]
            else:
                (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(path)
                flags = 0

            index[relative_path] = (ctime, mtime, dev, ino, mode, uid, gid, size, blob.id, flags)
            index.write()

            self.repo.object_store.add_object(blob)
    
    def stage_all(self):
        index = self._get_index()
        for status in self.status():
            if status in [AddedStatus, RemovedStatus, ModifiedStatus]:
                self.stage(self._get_absolute_path(status.path))

            if status == MissingStatus:
                del index[status.path]
                index.write()           

    def unstage(self, paths):
        index = self._get_index()

        if isinstance(paths, str):
            paths = [paths]
        
        for path in paths:
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
    
    def unstage_all(self):
        index = self._get_index()
        for status in self.status():
            self.unstage(self._get_absolute_path(status.path))
    
    def get_staged(self):
        staged = []
        tree = self._get_tree_at_head()
        index = self._get_index()
        if len(tree) > 0:
            for item in index.changes_from_tree(self.repo.object_store, tree.id):
                ((old_name, new_name), (old_mode, new_mode), (old_sha, new_sha)) = item

                staged.append(new_name)
                if old_name and old_name != new_name:
                    staged.append(old_name)
        
        return staged

    def is_staged(self, path):
        return (path in self.get_staged())
    
    def branch(self, name, commit_sha=None, track=False):
        if commit_sha:
            try:
                commit = self.repo.commit(commit_sha)
            except AssertionError:
                raise NotCommitError(commit_sha)
        else:
            commit = self.repo.commit(self.repo.head())

        self.repo.refs["refs/heads/%s" % name] = commit.id
        
        if track:
            self.track("refs/heads/%s" % name)
        
        return commit.id

    def branch_delete(self, name):
        ref_name = "refs/heads/%s" % name
        refs = self.repo.get_refs()
        if ref_name in refs:
            if self.is_tracking(ref_name):
                self.track("refs/heads/master")
        
            del self.repo.refs[ref_name]

    def branch_rename(self, old_name, new_name):
        old_ref_name = "refs/heads/%s" % old_name
        new_ref_name = "refs/heads/%s" % new_name
        refs = self.repo.get_refs()
        if old_ref_name in refs:
            self.repo.refs[new_ref_name] = self.repo.refs[old_ref_name]
            if self.is_tracking(old_ref_name):
                self.track(new_ref_name)
            
            del self.repo.refs[old_ref_name]

    def branch_list(self):
        refs = self.repo.get_refs()
        branches = []
        for ref,branch_sha in refs.items():
            if ref.startswith("refs/heads"):
                branch = Branch(ref[11:], branch_sha, self.repo[branch_sha])
                branches.append(branch)
        
        return branches

    def checkout(self, paths=[], tree_sha=None, commit_sha=None):
        tree = None
        if tree_sha:
            try:
                tree = self.repo.tree(tree_sha)
            except AssertionError:
                raise NotTreeError(tree_sha)
        elif commit_sha:
            try:
                commit = self.repo.commit(commit_sha)
                tree = commit.tree
            except AssertionError:
                raise NotCommitError(commit_sha)

        if not tree:
            tree = self._get_tree_at_head()

        relative_paths = []
        for path in paths:
            relative_paths = self._get_relative_path(path)

        for (name, mode, sha) in self.repo.object_store.iter_tree_contents(tree.id):
            if name in relative_paths or len(paths) == 0:
                self._write_blob_to_file(name, self.repo.get_blob(sha))
    
    def commit(self, message, parents=None, committer=None, commit_time=None, 
            commit_timezone=None, author=None, author_time=None, 
            author_timezone=None, encoding=None, commit_all=False):

        if commit_all:
            self.stage_all()

        commit = dulwich.objects.Commit()
        commit.message = message
        commit.tree = commit_index(self.repo.object_store, self._get_index())

        initial_commit = False
        try:
            commit.parents = (parents and parents or [self.repo.head()])
        except KeyError:
            # The initial commit has no parent
            initial_commit = True
            pass

        config_user = self._get_config_user()

        commit.committer = (committer and committer or config_user)
        commit.commit_time = (commit_time and commit_time or int(time()))
        commit.commit_timezone = (commit_timezone and commit_timezone or TZ)
        
        commit.author = (author and author or config_user)
        commit.author_time = (author_time and author_time or int(time()))
        commit.author_timezone = (author_timezone and author_timezone or TZ)        
        
        commit.encoding = (encoding and encoding or ENCODING)
        
        self.repo.object_store.add_object(commit)
        
        self.repo.refs[self.tracking()] = commit.id
        
        if initial_commit:
            self.track("refs/heads/master")

        return commit.id
    
    def tag(self, name, message, tagger=None, tag_time=None, tag_timezone=None,
            tag_object=None, track=False):
            
        tag = dulwich.objects.Tag()
        
        config_user = self._get_config_user()
        
        tag.name = name
        tag.message = message
        tag.tagger = (tagger and tagger or config_user)
        tag.tag_time = (tag_time and tag_time or int(time()))
        tag.tag_timezone = (tag_timezone and tag_timezone or TZ)
        
        if tag_object is None:
            tag_object = (DULWICH_COMMIT_TYPE, self.repo.head())

        tag.set_object(tag_object)

        self.repo.object_store.add_object(tag)
        
        self.repo.refs["refs/tags/%s" % name] = tag.id
        
        if track:
            self.track("refs/tags/%s" % name)
        
        return tag.id
    
    def tag_delete(self, name):
        ref_name = "refs/tags/%s" % name
        refs = self.repo.get_refs()
        if ref_name in refs:
            del self.repo.refs[ref_name]
    
    def tag_list(self):
        refs = self.repo.get_refs()
        tags = []
        for ref,tag_sha in refs.items():
            if ref.startswith("refs/tags"):
                tag = Tag(tag_sha, self.repo[tag_sha])
                tags.append(tag)
        
        return tags
    
    def status(self):
        tree = self._get_tree_at_head()
        index = self._get_index()
        paths = self._read_directory_tree(self.repo.path)
        
        statuses = []
        tracked_paths = set(index)
        if len(tree) > 0:
            for (name, mode, sha) in self.repo.object_store.iter_tree_contents(tree.id):
                absolute_path = self._get_absolute_path(name)
                if os.path.exists(absolute_path):
                    if name in tracked_paths:
                        # Cached, determine if modified or not
                        tracked_paths.remove(name)
                        
                        blob = self._get_blob_from_file(absolute_path)
                        if blob.id == index[name][8]:
                            statuses.append(NormalStatus(name))
                        else:
                            statuses.append(ModifiedStatus(name))
                    else:
                        # Removed
                        statuses.append(RemovedStatus(name))
                else:
                    # Missing
                    tracked_paths.remove(name)
                    statuses.append(MissingStatus(name))

                try:
                    paths.remove(name)
                except ValueError:
                    pass

        for name in tracked_paths:
            # Added
            statuses.append(AddedStatus(name))
            try:
                paths.remove(name)
            except ValueError:
                pass

        # Find untrackedfiles
        for path in paths:
            statuses.append(UntrackedStatus(path))

        return statuses
    
    def log(self):
        try:
            return self.repo.revision_history(self.repo.head())
        except dulwich.errors.NotCommitError:
            raise NotCommitError()
            return None
