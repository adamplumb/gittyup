#
# test/stage.py
#

import os
from shutil import rmtree
from sys import argv
from optparse import OptionParser

from cobragit.client import CobraGitClient
from cobragit.objects import *
from util import touch, change

parser = OptionParser()
parser.add_option("-c", "--cleanup", action="store_true", default=False)
(options, args) = parser.parse_args(argv)

DIR = "stage"

if options.cleanup:
    rmtree(DIR, ignore_errors=True)

    print "stage.py clean"
else:
    if os.path.isdir(DIR):
        raise SystemExit("This test script has already been run.  Please call this script with --cleanup to start again")

    os.mkdir(DIR)
    g = CobraGitClient()
    g.initialize_repository(DIR)
    
    touch(DIR + "/test1.txt")
    touch(DIR + "/test2.txt")
    
    # Stage both files
    g.stage([DIR+"/test1.txt", DIR+"/test2.txt"])
    st = g.status()
    assert (st[0] == CobraGitAddedStatus)
    assert (st[1] == CobraGitAddedStatus)
    
    # Unstage both files
    g.unstage([DIR+"/test1.txt", DIR+"/test2.txt"])
    st = g.status()
    assert (st[0] == CobraGitUntrackedStatus)
    assert (st[1] == CobraGitUntrackedStatus)
    
    # Untracked files should not be staged
    g.stage_all_changed()
    st = g.status()
    assert (st[0] == CobraGitUntrackedStatus)
    assert (st[1] == CobraGitUntrackedStatus)
    
    # test1.txt is changed now, so it should get staged and set as Modified
    g.stage([DIR+"/test1.txt"])
    g.commit("Test commit")
    change(DIR+"/test1.txt")
    g.stage_all_changed()
    st = g.status()
    assert (st[0] == CobraGitModifiedStatus)
    assert (st[1] == CobraGitUntrackedStatus)
    
    print "stage.py pass"
