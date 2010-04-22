#
# client.py
#

import os
import re
import shutil
import fnmatch
from time import time, timezone

import dulwich.errors
import dulwich.repo
import dulwich.objects
from dulwich.pack import Pack
from dulwich.index import commit_index, write_index_dict, SHA1Writer

from gittyup.exceptions import *
import gittyup.util
from gittyup.objects import *
from gittyup.config import GittyupLocalFallbackConfig
from gittyup.command import GittyupCommand

TZ = -1 * timezone
ENCODING = "UTF-8"

DULWICH_COMMIT_TYPE = 1
DULWICH_TREE_TYPE = 2
DULWICH_BLOB_TYPE = 3
DULWICH_TAG_TYPE = 4

def callback_notify_null(val):
    pass

class GittyupClient:
    def __init__(self, path=None, create=False):
        self.callback_notify = callback_notify_null
        self.global_ignore_patterns = []
        
        if path:
            try:
                self.repo = dulwich.repo.Repo(os.path.realpath(path))
                self._load_config()
                self.global_ignore_patterns = self._get_global_ignore_patterns()
            except dulwich.errors.NotGitRepository:
                if create:
                    self.initialize_repository(path)
                    self.global_ignore_patterns = self._get_global_ignore_patterns()
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
            tree = self.repo[self.repo[self.repo.head()].tree]
        except KeyError, e:
            tree = dulwich.objects.Tree()

        return tree

    def _get_working_tree(self):
        return self.repo[commit_index(self.repo.object_store, self._get_index())]

    def _get_tree_index(self, tree=None):
        if tree is None:
            tree = self._get_tree_at_head()

        tree_index = {}
        if tree:
            for item in self.repo.object_store.iter_tree_contents(tree.id):
                tree_index[item[0]] = (item[1], item[2])
        return tree_index

    def _get_global_ignore_patterns(self):
        """
        Get ignore patterns from $GIT_DIR/info/exclude then from
        core.excludesfile in gitconfig.
        
        """
        
        patterns = []
        try:
            git_dir = os.environ["GIT_DIR"]
        except KeyError:
            git_dir = self.repo.path

        excludefile = os.path.join(git_dir, "info", "exclude")
        if os.path.isfile(excludefile):
            patterns += self._get_ignore_patterns_from_file(excludefile)

        try:
            core_excludesfile = self.config.get("core", "excludesfile")
            if core_excludesfile:
                patterns += self._get_ignore_patterns_from_file(core_excludesfile)
        except KeyError:
            pass

        return patterns
    
    def _get_ignore_patterns_from_file(self, path):
        """
        Read in an ignore patterns file (i.e. .gitignore, $GIT_DIR/info/exclude)
        and return a list of patterns
        """
        
        patterns = []
        if os.path.isfile(path):
            file = open(path, "r")
            try:
                for line in file:
                    if line == "" or line.startswith("#"):
                        continue

                    patterns.append(line.rstrip("\n"))
            finally:
                file.close()
        
        return patterns

    def _ignore_file(self, patterns, filename):
        """
        Determine whether the given file should be ignored

        """
        for pattern in patterns:
            if fnmatch.fnmatch(filename, pattern) and not pattern.startswith("!"):
                return True

        return False
    
    def _read_directory_tree(self, path, show_ignored_files=False):
        files = []
        directories = []
        for root, dirs, filenames in os.walk(path, topdown=True):
            try:
                dirs.remove(".git")
            except ValueError:
                pass

            # Generate a list of appropriate ignore patterns
            patterns = []
            if not show_ignored_files:
                patterns = self.global_ignore_patterns

                path_to_check = root
                while path_to_check != self.repo.path:
                    patterns += self._get_ignore_patterns_from_file(os.path.join(path_to_check, ".gitignore"))
                    path_to_check = os.path.split(path_to_check)[0]
                
                patterns += self._get_ignore_patterns_from_file(os.path.join(root, ".gitignore"))

            # Find the relative root path of this folder
            if root == self.repo.path:
                rel_root = ""
            else:
                rel_root = self.get_relative_path(root)
                
            for filename in filenames:
                if not self._ignore_file(patterns, filename):
                    files.append(os.path.join(rel_root, filename))
        
            for _d in dirs:
                if not self._ignore_file(patterns, _d):
                    directories.append(os.path.join(rel_root, _d))
        
        directories.append("")
        return (sorted(files), directories)

    def _get_blob_from_file(self, path):
        file = open(path, "rb")
        try:
            blob = dulwich.objects.Blob.from_string(file.read())
        finally:
            file.close()
        
        return blob

    def _write_blob_to_file(self, path, blob):
        dirname = os.path.dirname(path)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
    
        file = open(path, "wb")
        try:
            file.write(blob.data)
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
    
    def _write_packed_refs(self, refs):
        packed_refs_str = ""
        for ref,sha in refs.items():
            packed_refs_str = "%s %s\n" % (sha, ref)
        
        fd = open(os.path.join(self.repo.controldir(), "packed-refs"), "wb")
        fd.write(packed_refs_str)
        fd.close()
    
    def _remove_from_index(self, index, key):
        del index._byname[key]
    
    #
    # Start Public Methods
    #
    
    def initialize_repository(self, path, bare=False):
        real_path = os.path.realpath(path)
        if not os.path.isdir(real_path):
            os.mkdir(real_path)

        if bare:
            self.repo = dulwich.repo.Repo.init_bare(real_path)
        else:
            self.repo = dulwich.repo.Repo.init(real_path)
            
        self._load_config()
        self.global_ignore_patterns = self._get_global_ignore_patterns()

        self.config.set_section("core", {
            "logallrefupdates": "true",
            "filemode": "true",
            "base": "false",
            "logallrefupdates": "true"
        })

    def set_repository(self, path):
        try:
            self.repo = dulwich.repo.Repo(os.path.realpath(path))
            self._load_config()
        except dulwich.errors.NotGitRepository:
            raise NotRepositoryError()

    def get_repository(self):
        return self.repo.path

    def find_repository_path(self, path):
        path_to_check = os.path.realpath(path)
        while path_to_check != "/" and path_to_check != "":
            if os.path.isdir(os.path.join(path_to_check, ".git")):
                return path_to_check
            
            path_to_check = os.path.split(path_to_check)[0]
        
        return None

    def get_relative_path(self, path):
        return gittyup.util.relativepath(os.path.realpath(self.repo.path), path)      
    
    def get_absolute_path(self, path):
        return os.path.join(self.repo.path, path).rstrip("/")

    def track(self, name):
        self.repo.refs["HEAD"] = self.repo.refs[name]

    def is_tracking(self, name):
        return (self.repo.refs["HEAD"] == self.repo.refs[name])

    def tracking(self):
        return self.repo.refs.read_ref("HEAD")[5:]
    
    def stage(self, paths):
        """
        Stage files to be committed or tracked
        
        @type   paths: list
        @param  paths: A list of files
        
        """

        index = self._get_index()

        if type(paths) in (str, unicode):
            paths = [paths]

        for path in paths:
            relative_path = self.get_relative_path(path)
            absolute_path = self.get_absolute_path(path)
            blob = self._get_blob_from_file(path)
            
            if relative_path in index:
                (ctime, mtime, dev, ino, mode, uid, gid, size, blob_id, flags) = index[relative_path]
            else:
                flags = 0

            # make sure mtime and ctime is updated every time a file is staged
            (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(path)

            index[relative_path] = (ctime, mtime, dev, ino, mode, uid, gid, size, blob.id, flags)
            index.write()

            self.repo.object_store.add_object(blob)
    
    def stage_all(self):
        """
        Stage all files in a repository to be committed or tracked
        
        """
        
        index = self._get_index()
        for status in self.status():
            if status in [AddedStatus, RemovedStatus, ModifiedStatus]:
                abs_path = self.get_absolute_path(status.path)
                if os.path.isfile(abs_path):
                    self.stage(abs_path)

            if status == MissingStatus:
                self._remove_from_index(index, status.path)
                index.write()           

    def unstage(self, paths):
        """
        Unstage files so they are not committed or tracked
        
        @type   paths: list
        @param  paths: A list of files
        
        """
        
        index = self._get_index()
        tree = self._get_tree_index()

        if type(paths) in (str, unicode):
            paths = [paths]

        for path in paths:
            relative_path = self.get_relative_path(path)
            if relative_path in index:
                if relative_path in tree:
                    (ctime, mtime, dev, ino, mode, uid, gid, size, blob_id, flags) = index[relative_path]
                    (mode, blob_id) = tree[relative_path]
                    
                    # If the file is locally modified, set these vars to 0
                    # I'm not sure yet why this needs to happen, but it does
                    # in order for the file to appear modified and not normal
                    blob = self._get_blob_from_file(path)
                    if blob.id != blob_id:
                        ctime = 0
                        mtime = 0
                        dev = 0
                        ino = 0
                        uid = 0
                        gid = 0
                        size = 0
                    
                    index[relative_path] = (ctime, mtime, dev, ino, mode, uid, gid, size, blob_id, flags)
                else:
                    self._remove_from_index(index, relative_path)
            else:
                if relative_path in tree:
                    index[relative_path] = (0, 0, 0, 0, tree[relative_path][0], 0, 0, 0, tree[relative_path][1], 0)

        index.write()
            
    def unstage_all(self):
        """
        Unstage all files so they are not committed or tracked
        
        @type   paths: list
        @param  paths: A list of files
        
        """
        
        index = self._get_index()
        for status in self.status():
            abs_path = self.get_absolute_path(status.path)
            if os.path.isfile(abs_path):
                self.unstage(abs_path)
    
    def get_staged(self):
        """
        Gets a list of files that are staged
        
        """

        staged = []
        tree = self._get_tree_at_head()
        index = self._get_index()

        if len(tree) > 0:
            for item in index.changes_from_tree(self.repo.object_store, tree.id):
                ((old_name, new_name), (old_mode, new_mode), (old_sha, new_sha)) = item

                if new_name:
                    staged.append(new_name)
                if old_name and old_name != new_name:
                    staged.append(old_name)
        else:
            for path in index:
                staged.append(path)

        return staged

    def is_staged(self, path, staged_files=None):
        """
        Determines if the specified path is staged
        
        @type   path: string
        @param  path: A file path
        
        @rtype  boolean
        
        """
        
        if not staged_files:
            staged_files = self.get_staged()
        
        relative_path = self.get_relative_path(path)
        return (relative_path in staged_files)
    
    def branch(self, name, commit_sha=None, track=False):
        """
        Create a new branch
        
        @type   name: string
        @param  name: The name of the new branch
        
        @type   commit_sha: string
        @param  commit_sha: A commit sha to branch from.  If None, branches
                    from head
        
        @type   track: boolean
        @param  track: Whether or not to track the new branch, or just create it
        
        """

        if commit_sha:
            try:
                commit = self.repo[commit_sha]
            except AssertionError:
                raise NotCommitError(commit_sha)
        else:
            commit = self.repo[self.repo.head()]

        self.repo.refs["refs/heads/%s" % name] = commit.id
        
        if track:
            self.track("refs/heads/%s" % name)
        
        return commit.id

    def branch_delete(self, name):
        """
        Delete a branch
        
        @type   name: string
        @param  name: The name of the branch
        
        """
        
        ref_name = "refs/heads/%s" % name
        refs = self.repo.get_refs()
        if ref_name in refs:
            if self.is_tracking(ref_name):
                self.track("refs/heads/master")
        
            del self.repo.refs[ref_name]

    def branch_rename(self, old_name, new_name):
        """
        Rename a branch

        @type   old_name: string
        @param  old_name: The name of the branch to be renamed

        @type   new_name: string
        @param  new_name: The name of the new branch

        """
        
        old_ref_name = "refs/heads/%s" % old_name
        new_ref_name = "refs/heads/%s" % new_name
        refs = self.repo.get_refs()
        if old_ref_name in refs:
            self.repo.refs[new_ref_name] = self.repo.refs[old_ref_name]
            if self.is_tracking(old_ref_name):
                self.track(new_ref_name)
            
            del self.repo.refs[old_ref_name]

    def branch_list(self):
        """
        List all branches
        
        """
        
        refs = self.repo.get_refs()
        branches = []
        for ref,branch_sha in refs.items():
            if ref.startswith("refs/heads"):
                branch = Branch(ref[11:], branch_sha, self.repo[branch_sha])
                branches.append(branch)
        
        return branches

    def checkout(self, paths=[], tree_sha=None, commit_sha=None):
        """
        Checkout a series of paths from a tree or commit.  If no tree or commit
        information is given, it will check out the files from head.  If no
        paths are given, all files will be checked out from head.
        
        @type   paths: list
        @param  paths: A list of files to checkout
        
        @type   tree_sha: string
        @param  tree_sha: The sha of a tree to checkout

        @type   commit_sha: string
        @param  commit_sha: The sha of a commit to checkout

        """
        
        tree = None
        if tree_sha:
            try:
                tree = self.repo[tree_sha]
            except AssertionError:
                raise NotTreeError(tree_sha)
        elif commit_sha:
            try:
                commit = self.repo[commit_sha]
                tree = commit.tree
            except AssertionError:
                raise NotCommitError(commit_sha)

        if not tree:
            tree = self._get_tree_at_head()

        relative_paths = []
        for path in paths:
            relative_paths = self.get_relative_path(path)

        index = self._get_index()
        for (name, mode, sha) in self.repo.object_store.iter_tree_contents(tree.id):
            if name in relative_paths or len(paths) == 0:
                blob = self.repo[sha]
                absolute_path = self.get_absolute_path(name)
                self._write_blob_to_file(absolute_path, blob)                

                (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(absolute_path)
                index[name] = (ctime, mtime, dev, ino, mode, uid, gid, size, blob.id, 0)
    
    def clone(self, host, path, bare=False, origin="origin"):
        """
        Clone a repository
        
        @type   host: string
        @param  host: The url of the git repository
        
        @type   path: string
        @param  path: The path to clone to
        
        @type   bare: boolean
        @param  bare: Create a bare repository or not
        
        @type   origin: string
        @param  origin: Specify the origin of the repository

        """
    
        more = ["-o", "origin"]
        if bare:
            more.append("--bare")
    
        base_dir = os.path.split(path)[0]
    
        cmd = ["git", "clone", host, path] + more
        try:
            (status, stdout, stderr) = GittyupCommand(cmd, cwd=base_dir, notify=self.callback_notify).execute()
        except GittyupCommandError, e:
            print e
    
    def commit(self, message, parents=None, committer=None, commit_time=None, 
            commit_timezone=None, author=None, author_time=None, 
            author_timezone=None, encoding=None, commit_all=False):
        """
        Commit staged files to the local repository
        
        @type   message: string
        @param  message: The log message
        
        @type   parents: list
        @param  parents: A list of parent SHAs.  Defaults to head.
        
        @type   committer: string
        @param  committer: The person committing.  Defaults to 
            "user.name <user.email>"
        
        @type   commit_time: int
        @param  commit_time: The commit time.  Defaults to time.time()
        
        @type   commit_timezone: int
        @param  commit_timezone: The commit timezone.  
            Defaults to (-1 * time.timezone)
        
        @type   author: string
        @param  author: The author of the file changes.  Defaults to 
            "user.name <user.email>"
            
        @type   author_time: int
        @param  author_time: The author time.  Defaults to time.time()
        
        @type   author_timezone: int
        @param  author_timezone: The author timezone.  
            Defaults to (-1 * time.timezone)
        
        @type   encoding: string
        @param  encoding: The encoding of the commit.  Defaults to UTF-8.
        
        @type   commit_all: boolean
        @param  commit_all: Stage all changed files before committing
        
        """

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
        if config_user is None:
            if committer is None:
                raise ValueError("The committing person has not been specified")
            if author is None:
                raise ValueError("The author has not been specified")

        commit.committer = (committer and committer or config_user)
        commit.commit_time = (commit_time and commit_time or int(time()))
        commit.commit_timezone = (commit_timezone and commit_timezone or TZ)
        
        commit.author = (author and author or config_user)
        commit.author_time = (author_time and author_time or int(time()))
        commit.author_timezone = (author_timezone and author_timezone or TZ)        
        
        commit.encoding = (encoding and encoding or ENCODING)
        
        self.repo.object_store.add_object(commit)
        
        self.repo.refs["HEAD"] = commit.id
        
        if initial_commit:
            self.track("refs/heads/master")
            
        return commit.id
    
    def remove(self, paths):
        """
        Remove path from the repository.  Also deletes the local file.
        
        @type   paths: list
        @param  paths: A list of paths to remove
        
        """
        
        if type(paths) in (str, unicode):
            paths = [paths]

        index = self._get_index()
        
        for path in paths:
            relative_path = self.get_relative_path(path)
            if relative_path in index:
                self._remove_from_index(index, relative_path)
                os.remove(path)

        index.write()        
    
    def move(self, source, dest):
        """
        Move a file within the repository
        
        @type   source: string
        @param  source: The source file
        
        @type   dest: string
        @param  dest: The destination.  If dest exists as a directory, source
            will be added as a child.  Otherwise, source will be renamed to
            dest.
            
        """
        
        index = self._get_index()
        relative_source = self.get_relative_path(source)
        relative_dest = self.get_relative_path(dest)

        # Get a list of affected files so we can update the index
        source_files = []
        if os.path.isdir(source):
            for name in index:
                if name.startswith(relative_source):
                    source_files.append(name)
        else:
            source_files.append(self.get_relative_path(source))

        # Rename the affected index entries
        for source_file in source_files:
            new_path = source_file.replace(relative_source, relative_dest)            
            if os.path.isdir(dest):
                new_path = os.path.join(new_path, os.path.basename(source_file))

            index[new_path] = index[source_file]
            self._remove_from_index(index, source_file)

        index.write()
        
        # Actually move the file/folder
        shutil.move(source, dest)

    def pull(self, repository="origin", refspec="master"):
        """
        Fetch objects from a remote repository and merge with the local 
            repository
            
        @type   repository: string
        @param  repository: The name of the repository
        
        @type   refspec: string
        @param  refspec: The branch name to pull from
        
        """
        
        cmd = ["git", "pull", repository, refspec]
        try:
            (status, stdout, stderr) = GittyupCommand(cmd, cwd=self.repo.path).execute()
        except GittyupCommandError, e:
            print e
    
    def push(self, repository="origin", refspec="master"):
        """
        Push objects from the local repository into the remote repository
            and merge them.
            
        @type   repository: string
        @param  repository: The name of the repository
        
        @type   refspec: string
        @param  refspec: The branch name to pull from
        
        """

        cmd = ["git", "push", repository, refspec]
        try:
            (status, stdout, stderr) = GittyupCommand(cmd, cwd=self.repo.path).execute()
        except GittyupCommandError, e:
            print e

    def fetch(self, host):
        """
        Fetch objects from a remote repository.  This will not merge the files
            into the local working copy, use pull for that.
        
        @type   host: string
        @param  host: The git url from which to fetch
        
        """
        
        client, host_path = gittyup.util.get_transport_and_path(host)

        graphwalker = self.repo.get_graph_walker()
        f, commit = self.repo.object_store.add_pack()
        refs = client.fetch_pack(host_path, self.repo.object_store.determine_wants_all, 
                          graphwalker, f.write, self.callback_notify)

        commit()
        
        return refs
    
    def remote_add(self, host, origin="origin"):
        """
        Add a remote repository
        
        @type   host: string
        @param  host: The git url to add
        
        @type   origin: string
        @param  origin: The name to give to the remote repository
        
        """
        
        self.config.set("remote \"%s\"" % origin, "fetch", "+refs/heads/*:refs/remotes/%s/*" % origin)
        self.config.set("remote \"%s\"" % origin, "url", host)
        self.config.write()
    
    def remote_delete(self, origin="origin"):
        """
        Remove a remote repository
        
        @type   origin: string
        @param  origin: The name of the remote repository to remove

        """
        
        self.config.remove_section("remote \"%s\"" % origin)
        self.config.write()
    
    def remote_list(self):
        """
        Return a list of the remote repositories
        
        @rtype  list
        @return A list of dicts with keys: remote, url, fetch
            
        """
        
        ret = []
        for section, values in self.config.get_all():
            if section.startswith("remote"):
                m = re.match("^remote \"(.*?)\"$", section)
                if m:
                    ret.append({
                        "remote": m.group(1),
                        "url": values["url"],
                        "fetch": values["fetch"]
                    })

        return ret
    
    def tag(self, name, message, tagger=None, tag_time=None, tag_timezone=None,
            tag_object=None, track=False):
        """
        Create a tag object
        
        @type   name: string
        @param  name: The name to give the tag
        
        @type   message: string
        @param  message: A log message
        
        @type   tagger: string
        @param  tagger: The person tagging.  Defaults to 
            "user.name <user.email>"
        
        @type   tag_time: int
        @param  tag_time: The tag time.  Defaults to time.time()
        
        @type   tag_timezone: int
        @param  tag_timezone: The tag timezone.  
            Defaults to (-1 * time.timezone)
        
        @type   tag_object: string
        @param  tag_object: The object to tag.  Defaults to HEAD
        
        @type   track: boolean
        @param  track: Whether or not to track the tag
        
        """
        
        tag = dulwich.objects.Tag()
        
        config_user = self._get_config_user()

        if config_user is None:
            if tagger is None:
                raise ValueError("The tagging person has not been specified")
        
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
        """
        Delete a tag
        
        @type   name: string
        @param  name: The name of the tag to delete
        
        """
        
        ref_name = "refs/tags/%s" % name
        refs = self.repo.get_refs()
        if ref_name in refs:
            del self.repo.refs[ref_name]
    
    def tag_list(self):
        """
        Return a list of Tag objects
        
        """
    
        refs = self.repo.get_refs()
        tags = []
        for ref,tag_sha in refs.items():
            if ref.startswith("refs/tags"):
                tag = Tag(tag_sha, self.repo[tag_sha])
                tags.append(tag)
        
        return tags
    
    def status(self, paths_to_return=[]):
        """
        Generates a list of GittyupStatus objects for all files in the 
            repository.
        
        """

        if type(paths_to_return) in (str, unicode):
            paths_to_return = [paths_to_return]
    
        tree = self._get_tree_at_head()
        tree_index = self._get_tree_index(tree)
        index = self._get_index()
        (files, directories) = self._read_directory_tree(self.repo.path)

        statuses = []
        tracked_paths = set(index)
        if len(tree_index) > 0:
            for (name, mode, sha) in self.repo.object_store.iter_tree_contents(tree.id):
                if name in tracked_paths:
                    if name in tree_index:
                        absolute_path = self.get_absolute_path(name)
                        if os.path.exists(absolute_path):
                            # Cached, determine if modified or not                        
                            blob = self._get_blob_from_file(absolute_path)
                            if blob.id == tree_index[name][1]:
                                statuses.append(NormalStatus(name))
                            else:
                                statuses.append(ModifiedStatus(name))
                        else:
                            # Missing
                            statuses.append(MissingStatus(name))
                    else:
                        statuses.append(AddedStatus(name))
                        
                    tracked_paths.remove(name)
                else:
                    # Removed
                    statuses.append(RemovedStatus(name))

                try:
                    files.remove(name)
                except ValueError:
                    pass

        for name in tracked_paths:
            # Added
            statuses.append(AddedStatus(name))
            try:
                files.remove(name)
            except ValueError:
                pass

        # Find untracked files
        for f in files:
            statuses.append(UntrackedStatus(f))

        # If path is specified as a parameter, narrow the list down
        final_statuses = []
        if len(paths_to_return) > 0:
            for path_to_return in paths_to_return:
                if path_to_return and self.get_absolute_path(path_to_return) != self.repo.path:
                    relative_path = self.get_relative_path(path_to_return)
                    if os.path.isdir(path_to_return):
                        for st in statuses:
                            if st.path.startswith(relative_path) or relative_path == "":
                                final_statuses.append(st)
                    elif os.path.isfile(path_to_return):
                        for st in statuses:
                            if st.path == relative_path:
                                final_statuses.append(st)
                                break
                else:
                    final_statuses = statuses
                    break
        else:
            final_statuses = statuses
            
        del statuses

        # Determine status of folders based on child contents
        for d in directories:
            d_status = NormalStatus(d)
            for st in final_statuses:
                if os.path.join(d, os.path.basename(st.path)) == st.path:

                    if st.identifier != "normal" and st.identifier != "untracked":
                        d_status = ModifiedStatus(d)
            

            final_statuses.append(d_status)

        # Calculate which files are staged
        staged_files = self.get_staged()
        for index,st in enumerate(final_statuses):
            final_statuses[index].is_staged = (st.path in staged_files)

        return final_statuses
    
    def log(self):
        """
        Returns a revision history list
        
        """
        
        try:
            return self.repo.revision_history(self.repo.head())
        except dulwich.errors.NotCommitError:
            raise NotCommitError()
            return None

    def set_callback_notify(self, func):
        self.callback_notify = func
    
    def notify(self, data):
        if self.callback_notify is not None:
            self.callback_notify(data)
