#
# test/remote.py
#

import os
from shutil import rmtree
from sys import argv
from optparse import OptionParser

from gittyup.client import GittyupClient
from util import touch

parser = OptionParser()
parser.add_option("-c", "--cleanup", action="store_true", default=False)
(options, args) = parser.parse_args(argv)

DIR = "remote"

if options.cleanup:
    rmtree(DIR, ignore_errors=True)

    print "remote.py clean"
else:
    if os.path.isdir(DIR):
        raise SystemExit("This test script has already been run.  Please call this script with --cleanup to start again")

    os.mkdir(DIR)
    g = GittyupClient(DIR, create=True)
    g.remote_add("git://github.com/adamplumb/sprout.git", "origin")
    l = g.remote_list()

    assert (len(l) == 1)
    assert (l[0]["url"] == "git://github.com/adamplumb/sprout.git")
    
    g.remote_delete("origin")
    l = g.remote_list()
    
    assert (len(l) == 0)

    print "remote.py pass"
