#
# test/stage.py
#

import os
from shutil import rmtree
from sys import argv
from optparse import OptionParser

from cobragit.client import CobraGitClient
from util import touch

parser = OptionParser()
parser.add_option("-c", "--cleanup", action="store_true", default=False)
(options, args) = parser.parse_args(argv)

DIR = "branch"

if options.cleanup:
    rmtree(DIR, ignore_errors=True)

    print "branch.py clean"
else:
    if os.path.isdir(DIR):
        raise SystemExit("This test script has already been run.  Please call this script with --cleanup to start again")

    os.mkdir(DIR)
    g = CobraGitClient()
    g.initialize_repository(DIR)
    
    touch(DIR + "/test1.txt")
    touch(DIR + "/test2.txt")
    
    g.stage([DIR+"/test1.txt", DIR+"/test2.txt"])
    g.commit("This is a commit")
    
    assert ("master" in g.branch_list())
    
    g.branch("branch1")

    assert ("branch1" in g.branch_list())
    
    g.branch_rename("branch1", "branch1b")

    assert ("branch1b" in g.branch_list())
    
    g.branch_delete("branch1")
    
    assert ("branch1" not in g.branch_list())

    print "branch.py pass"
