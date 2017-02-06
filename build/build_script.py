#!/usr/bin/env python
# -*- coding: utf-8 -*-

# build fully, but not commit also:
# usage: python ./build/build_script.py . dev

from os import path, walk, chdir, remove, system
from glob import glob
import time
import json
import hashlib
import argparse
import subprocess

parser = argparse.ArgumentParser(
    description='Build script for Wrapper.py!',
    epilog='Created by Jason Bristol')

parser.add_argument('source', type=str, default='.',
                    help='the top level source directory')
parser.add_argument('branch', type=str, choices=('dev', 'stable'),
                    default='dev', help='branch to commit changes to')
parser.add_argument('--commit', '-c', action='store_true',
                    help='commit changes to specified branch')
parser.add_argument('--message', '-m', type=str, default='build revision',
                    help='commit message')
parser.add_argument('--verbose', '-v', action='store_true',
                    help='verbose flag')

args = parser.parse_args()


def build_the_events():
    """Build a Rst table(s) describing wrapper events"""

    # Sample event doc
    ''' EventDoc
        Required items-
        <gr> player <gr> group
        <desc> When player places a block or item. <desc> description
        <abortable>
        Block placement can be rejected by returning False.
        <abortable>

        Optional items-
        # uses the call event payload if not specified.
        :payload:
        {"player": the player,
        "command": what he was up to,
        "args": what he said}
        :payload:

        # omitted if not specified
        :args:
            :"position":
             Where new block or item will go (corrected for "face".
            :"clickposition": The cooridinates actually clicked on.
        :args:

    '''
    all_events = ""
    codefiles = [
        y for x in walk("wrapper") for y in glob(path.join(x[0], '*.py'))]
    # so that they are always in the same order..
    codefiles.sort()

    for filenames in codefiles:
        with open(filenames) as f:
            file = f.read()

        eventlist = file.split("events.callevent(")
        for event in eventlist:
            # has a document
            if "''' EventDoc" in event:
                # get callevent name and payload, newlines removed...
                eventargs = event.split("):")[
                    0].strip("\n").lstrip(" ").rstrip(" ")

                eventname, pay = eventargs.split(", ")[:2]
                eventname = ":%s:" % eventname.split(",")[0]
                pay = "{%s}" % pay

                # use alternate payload text
                if ":payload:" in event:
                    pay = event.split(":payload:")[1]

                aborthandling = event.split("<abortable>\n")[
                    1].lstrip().rstrip()
                print(pay)
                payload = pay.replace(
                    "  ", "").replace("\n", "").replace(
                    "{\"", "\n            :\"").replace(
                    "}", "").replace(
                    ",\"", "\n            :\"").replace(
                    ", \"", ",\n            :\"")

                print(payload)
                # groupname is for sorting
                groupname = event.split(" <gr> ")[1]
                description = ":description: %s" % event.split(" <desc> ")[1]
                event_item = "    %s\n\n        %s\n" \
                             "        :payload:\n%s\n" \
                             "        :abortable: %s\n\n" % \
                             (eventname, description,
                              payload, aborthandling)
                all_events += event_item
    return all_events


def build_the_docs(events):
    """

    Simple docs builder.  creates 'ReStructured Text' files from the
    docstrings. Rst format based on spec:

    http://docutils.sourceforge.net/docs/ref/rst/restructuredtext.html

    """

    sep = '"""'
    index_file = "**Welcome to the Wrapper.py Plugin API documentation!" \
                 "**\n\nThe API is divided into modules.  Click on each " \
                 "module to see it's documentation.\n\n\n"

    api_files = ["wrapperconfig", "base", "minecraft", "player", "world",
                 "entity", "backups", "helpers"]
    processed = {}

    for files in api_files:
        with open("wrapper/api/%s.py" % files) as f:
            data = f.read()
        all_items = data.split(sep)
        complete_doc = ""
        item_count = len(all_items) - 1
        total_items = range(0, item_count, 2)
        for each_item in total_items:
            # each_item.split(endsep)[0]
            item = all_items[each_item + 1]
            header = "****\n"
            if "class " in all_items[each_item]:
                header = "**< class%s >**\n" % all_items[each_item].split(
                    "class")[1].split(":")[0]

            if "def " in all_items[each_item]:
                defs = all_items[each_item].split("def")
                number_of_defs = len(defs) - 1
                header = "- %s\n" % all_items[each_item].split(
                    "def")[number_of_defs].split(":")[0]

            # dont create documentation for private functions
            if "-  _" not in header:
                complete_doc = "%s\n%s%s\n" % (complete_doc, header, item)

        processed[files] = complete_doc

    for files in api_files:
        with open("documentation/%s.rst" % files, "w") as f:
            f.write(processed[files])
        index_file = "%s[%s](/documentation/%s.rst)\n\n" % (
            index_file, files, files)

    with open("documentation/index.md", "w") as f:
        f.write(index_file)

    with open("documentation/events.rst", "w") as f:
        f.write("%s\n\n" % events)


def build_wrapper(buildargs):
    chdir(buildargs.source)

    # build the events
    events = build_the_events()

    # build the docs
    build_the_docs(events)

    with open("build/version.json", "r") as f:
        version = json.loads(f.read())
        if "__build__" not in version:
            version["__build__"] = version["build"] + 1
        else:
            version["__build__"] += 1
        version["__branch__"] = buildargs.branch
        version["release_time"] = time.time()

    filetext = ("# -*- coding: utf-8 -*-\n"
                "# Do not edit this file to bump versions; "
                "it is built automatically"
                "\n\n__version__ = %s\n__build__ = %d\n__branch__ = '%s'\n" %
                (version["__version__"], version["__build__"],
                 version["__branch__"]))

    with open("build/buildinfo.py", "w") as f:
        f.write(filetext)

    with open("wrapper/core/buildinfo.py", "w") as f:
        f.write(filetext)

    with open("build/version.json", "w") as f:
        f.write(json.dumps(version, indent=4, sort_keys=True))

    if path.exists("Wrapper.py"):
        remove("Wrapper.py")  # Time to start with a clean Wrapper.py!
    # subprocess.Popen("zip Wrapper.py -r . -x *~ -x *pyc", shell=True).wait()

    # from the master branch (this works properly)
    # Hooray for calling zip from system() instead of using proper
    # modules! :D
    print(path.curdir)
    system("ls")
    chdir("wrapper")
    system("zip ../Wrapper.py -r . -x *~ /.git* *.pyc")
    chdir("..")
    system("zip Wrapper.py LICENSE.txt")

    with open("./build/Wrapper.py.md5", "w") as f:
        f.write(hashlib.md5(open("./Wrapper.py", "rb").read()).hexdigest())

    # Mainly just for me (benbaptist), since most people will probably
    # want to build locally without committing.
    if buildargs.commit:
        subprocess.Popen("git add --update :/", shell=True).wait()
        subprocess.Popen(
            "git commit -m 'Build %s %d | %s'" %
            (buildargs.branch, version["__build__"], buildargs.message),
            shell=True).wait()
        subprocess.Popen("git push", shell=True).wait()
    print("Built version %d (%s build)" % (
        version["__build__"], buildargs.branch))

# Don't try-except here (just hides errors)
build_wrapper(args)
