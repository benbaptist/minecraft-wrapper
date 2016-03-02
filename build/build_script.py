#!/usr/bin/env python

import os, sys, time, json, hashlib, argparse, zipfile, subprocess

parser = argparse.ArgumentParser(
  description='Build script for Wrapper.py!', 
  epilog='Created by Jason Bristol')

parser.add_argument('source', type=str, default='.', help='the top level source directory')
parser.add_argument('branch', type=str, choices=('dev', 'stable'), default='dev', help='branch to commit changes to')
parser.add_argument('--commit',  '-c', action='store_true', help='commit changes to specified branch')
parser.add_argument('--message', '-m', type=str, default='build revision', help='commit message') 
parser.add_argument('--verbose', '-v', action='store_true', help='verbose flag')

args = parser.parse_args()

def build_wrapper(args):
  os.chdir(args.source)

  with open("build/version.json", "r") as f:
    version = json.loads(f.read())
    version["build"] += 1
    version["type"] = args.branch
    version["release_time"] = time.time()

  with open("globals.py", "w") as f:
    f.write("build=%d\ntype='%s'" % (version["build"], args.branch))

  with open("build/version.json", "w") as f:
    f.write(json.dumps(version))

  if os.path.exists("Wrapper.py"): os.remove("Wrapper.py") # Time to start with a clean Wrapper.py!
  # subprocess.Popen("zip Wrapper.py -r . -x *~ -x *pyc", shell=True).wait()

  if args.verbose: print 'Creating Archive...'
  zf = zipfile.ZipFile('Wrapper.py', mode='w')
  try:
    if args.verbose: print 'Adding Files...'
    for root, dirs, files in os.walk("src"):
      for f in files:
        path = os.path.join(root, f)
        if args.verbose: print 'Archiving %s...' % path
        zf.write(path, arcname=path[4:])
  finally:
    if args.verbose: print 'Closing Archive...'
    zf.close()

  with open("Wrapper.py", "r") as f:
    content = f.read()

  with open("build/Wrapper.py.md5", "w") as f:
    f.write(hashlib.md5(content).hexdigest())

  if args.commit: # Mainly just for me (benbaptist), since most people will probably want to build locally without committing to anything
    subprocess.Popen("git add --update :/", shell=True).wait()
    subprocess.Popen("git commit -m 'Build %s %d | %s'" % (args.branch, version["build"], args.message), shell=True).wait()
    subprocess.Popen("git push", shell=True).wait()
  print "Built version %d (%s build)" % (version["build"], args.branch)

try:    build_wrapper(args)
except: print "\n{}: {}\n".format("Unexpected error", sys.exc_info()[1])