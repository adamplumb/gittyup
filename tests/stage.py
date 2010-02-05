#
# test/stage.py
#

import os
from shutil import rmtree
from sys import argv
from optparse import OptionParser

from cobragit.client import GittyupClient
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
    g = GittyupClient()
    g.initialize_repository(DIR)
    
    touch(DIR + "/test1.txt")
    touch(DIR + "/test2.txt")
    
    # Stage both files
    g.stage([DIR+"/test1.txt", DIR+"/test2.txt"])
    st = g.status()
    assert (st[0] == GittyupAddedStatus)
    assert (st[1] == GittyupAddedStatus)
    
    # Unstage both files
    g.unstage([DIR+"/test1.txt", DIR+"/test2.txt"])
    st = g.status()
    assert (st[0] == GittyupUntrackedStatus)
    assert (st[1] == GittyupUntrackedStatus)
    
    # Untracked files should not be staged
    g.stage_all()
    st = g.status()
    assert (st[0] == GittyupUntrackedStatus)
    assert (st[1] == GittyupUntrackedStatus)
    
    # test1.txt is changed, so it should get staged and set as Modified
    g.stage([DIR+"/test1.txt"])
    g.commit("Test commit")
    change(DIR+"/test1.txt")
    g.stage_all_changed()
    st = g.status()
    assert (g.is_staged(st[0].path))
    assert (not g.is_staged(st[1].path))

    # Unstage all staged files
    g.unstage_all()
    st = g.status()
    assert (not g.is_staged(st[0].path))
    assert (not g.is_staged(st[1].path))
    
    print "stage.py pass"
