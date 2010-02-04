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

DIR = "unstage"

if options.cleanup:
    rmtree(DIR)

    print "unstage.py clean"
else:
    if os.path.isdir(DIR):
        raise SystemExit("This test script has already been run.  Please call this script with --cleanup to start again")

    os.mkdir(DIR)
    g = CobraGitClient()
    g.initialize_repository(DIR)
    
    touch(DIR + "/test1.txt")
    touch(DIR + "/test2.txt")
    
    g.stage([DIR+"/test1.txt", DIR+"/test2.txt"])    
    g.unstage([DIR+"/test1.txt", DIR+"/test2.txt"])
    
    st = g.status()
    
    if st[0].identifier == "untracked" and st[1].identifier == "untracked":
        print "unstage.py pass"
    else:
        print "unstage.py fail"
