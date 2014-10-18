#!/usr/bin/env python
""" Welcome to my sloppy build script for Wrapper.py! Hope you enjoy this wonderful work of sloppy art!

Also, I just realized: Why do I have the build and commit/push functionality all in one file? I really ought to do that separately. I'm weird. 
"""
import os, time, sys, json, sys
COMMIT = False
if os.path.exists("ZOMG_OHAI"): COMMIT = True # This script is a work of art. Creating a file named ZOMG_OHAI to turn on git committing? Pure genius.
if len(sys.argv) < 2:
	print "Usage: build.py <stable/dev>" # Note: an extra argument, "commit message", should be passed to the script if COMMIT is turned on. You must pass that argument in quotes or escape spaces with \. 
	print "Unless you intend this build to be used in the main repository, set it to dev!"
	sys.exit(0)
buildType = sys.argv[1]
if buildType not in ("dev", "stable"): # This is how real programmers do it. Yeah! Woohoo! Fine art programming!
	print "Invalid build type! dev or stable"
	sys.exit(0)
os.chdir("src")
with open("../docs/version.json", "r") as f:
	version = json.loads(f.read())
	version["build"] += 1
	version["type"] = buildType
with open("globals.py", "w") as f:
	f.write("build=%d\ntype='%s'" % (version["build"], buildType))
with open("../docs/version.json", "w") as f:
	f.write(json.dumps(version))
os.remove("../Wrapper.py") # Time to start with a clean Wrapper.py!
os.system("zip ../Wrapper.py -r . -x *~ -x *pyc") # Hooray for calling zip from os.system() instead of using proper modules! :D
if COMMIT: # Mainly just for me (benbaptist), since most people will probably want to build locally without committing to anything
	os.system("git add --update :/")
	os.system("git commit -m 'Build %s %d | %s'" % (buildType, version["build"], sys.argv[2]))
	os.system("git push")
print "Built version %d (%s build)" % (version["build"], buildType)
