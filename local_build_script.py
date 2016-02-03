#!/usr/bin/env python
""" Welcome to my sloppy build script for Wrapper.py! Hope you enjoy this wonderful work of sloppy art!

Also, I just realized: Why do I have the build and commit/push functionality all in one file? I really ought to do that separately. I'm weird. 
"""
import os, time, sys, json, sys, hashlib
os.chdir("/home/surest/Desktop/remotemcwrapper_dev/src")
os.remove("../Wrapper.py") # Time to start with a clean Wrapper.py!
os.system("zip ../Wrapper.py -r . -x *~ -x *pyc") # Hooray for calling zip from os.system() instead of using proper modules! :D
with open("../docs/Wrapper.py.md5", "w") as f:
	f.write(hashlib.md5(open("../Wrapper.py", "r").read()).hexdigest())

