#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import json
import hashlib
import argparse
import zipfile
import subprocess

parser = argparse.ArgumentParser(
    description='Build script for Wrapper.py!',
    epilog='Created by Jason Bristol')

parser.add_argument('source', type=str, default='.', help='the top level source directory')
parser.add_argument('branch', type=str, choices=('dev', 'stable'), default='dev',
                    help='branch to commit changes to')
parser.add_argument('--commit', '-c', action='store_true', help='commit changes to specified branch')
parser.add_argument('--message', '-m', type=str, default='build revision', help='commit message') 
parser.add_argument('--verbose', '-v', action='store_true', help='verbose flag')

args = parser.parse_args()


def build_wrapper(buildargs):
    os.chdir(buildargs.source)

    with open("build/version.json", "r") as f:
        version = json.loads(f.read())
        version["__build__"] += 1
        version["__branch__"] = buildargs.branch
        version["release_time"] = time.time()

    with open("core/buildinfo.py", "w") as f:
        f.write("__build__=%d\n__branch__='%s'" % (version["build"], buildargs.branch))

    with open("build/version.json", "w") as f:
        f.write(json.dumps(version))

    if os.path.exists("Wrapper.py"):
        os.remove("Wrapper.py")  # Time to start with a clean Wrapper.py!
    # subprocess.Popen("zip Wrapper.py -r . -x *~ -x *pyc", shell=True).wait()

    if buildargs.verbose:
        print('Creating Archive...')
    zf = zipfile.ZipFile('Wrapper.py', mode='w')
    try:
        if buildargs.verbose:
            print('Adding Files...')
        for root, dirs, files in os.walk("wrapper"):
            for f in files:
                path = os.path.join(root, f)
                if buildargs.verbose:
                    print('Archiving %s...' % path)
                zf.write(path, arcname=path[4:])
    finally:
        if buildargs.verbose:
            print('Closing Archive...')
        zf.close()

    with open("Wrapper.py", "r") as f:
        content = f.read()

    with open("build/Wrapper.py.md5", "w") as f:
        f.write(hashlib.md5(content).hexdigest())

    # Mainly just for me (benbaptist), since most people will probably want to build locally without committing.
    if buildargs.commit:
        subprocess.Popen("git add --update :/", shell=True).wait()
        subprocess.Popen("git commit -m 'Build %s %d | %s'" % (buildargs.branch, version["__build__"],
                                                               buildargs.message),
                         shell=True).wait()
        subprocess.Popen("git push", shell=True).wait()
    print("Built version %d (%s build)" % (version["__build__"], buildargs.branch))

try:
    build_wrapper(args)
except Exception as e:
    print("Unexpected error: \n%s", e)
