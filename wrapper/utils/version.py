# -*- coding: utf-8 -*-
# modified by SurestTexas00

# Copyright (c) Django Software Foundation and individual contributors.
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

#     1. Redistributions of source code must retain the above copyright notice,
#        this list of conditions and the following disclaimer.

#     2. Redistributions in binary form must reproduce the above copyright
#        notice, this list of conditions and the following disclaimer in the
#        documentation and/or other materials provided with the distribution.

#     3. Neither the name of Django nor the names of its contributors may be
#        used to endorse or promote products derived from this software without
#        specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from __future__ import unicode_literals

import datetime
import os
import subprocess


def get_version(version=None):
    """Returns a PEP 440-compliant version number from VERSION."""
    version = get_complete_version(version)

    # Now build the two parts of the version number:
    # main = X.Y[.Z]
    # sub = .devN - for pre-alpha releases
    #     | {a|b|rc}N - for alpha, beta, and rc releases

    main = get_main_version(version)

    sub = ''
    if version[3] == 'alpha' and version[4] == 0:
        git_changeset = get_git_changeset()
        if git_changeset:
            sub = '.dev%s' % git_changeset

    elif version[3] != 'final':
        mapping = {'alpha': 'a', 'beta': 'b', 'rc': 'rc'}
        sub = mapping[version[3]] + str(version[4])

    return str(main + sub)


def get_main_version(version=None):
    """Returns main version (X.Y[.Z]) from VERSION."""
    version = get_complete_version(version)
    parts = 2 if version[2] == 0 else 3
    return str('.'.join(str(x) for x in version[:parts]))


def get_complete_version(version=None):
    """Returns a tuple of the django version. If version argument is non-empty,
    then checks for correctness of the tuple provided.
    """
    if version is None:
        from core.buildinfo import __version__ as version
    else:
        assert len(version) == 5
        assert version[3] in ('alpha', 'beta', 'rc', 'final')

    return version


def get_docs_version(version=None):
    """ since this is usually designed to get a docs repo, the names
    are tied to corresponding Wrapper repo expected to house these releases"""
    version = get_complete_version(version)
    if version[3] == 'final':
        repo = 'master'
    elif version[3] == 'rc':
        repo = 'development'
    else:
        repo = 'experimental'
    return str(repo)


def get_git_changeset(formatter=True):
    """
    **We really can't use this at the present time because builds_script.py
    is run PRIOR to comitting.  This means our identifier would actually
    be for the LAST build, not the present one.**

    Returns a string representation of numeric identifier of the latest
    git changeset.

    The result is the UTC timestamp of the changeset in YYYYMMDDHHMMSS format.
    This value isn't guaranteed to be unique, but collisions are very unlikely,
    so it's sufficient for generating the development version numbers.

    A more compact, less readable, EPOCH time can be returned by specifying
    `formatter=False`
    """
    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    git_log = subprocess.Popen(
        'git log --pretty=format:%ct --quiet -1 HEAD',
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        shell=True, cwd=repo_dir, universal_newlines=True,
    )
    timestamp = git_log.communicate()[0]
    if formatter:
        try:
            timestamp = datetime.datetime.utcfromtimestamp(int(timestamp))
        except ValueError:
            return None
        return timestamp.strftime('%Y%m%d%H%M%S')
    else:
        return timestamp


if __name__ == "__main__":
    print(get_version(), "get_version()")
    print(get_main_version(), "get_main_version()")
    print(get_complete_version(), "get_complete_version()")
    print(get_docs_version(), "get_docs_version()")
    print(get_git_changeset(formatter=False), "get_git_changeset()")
