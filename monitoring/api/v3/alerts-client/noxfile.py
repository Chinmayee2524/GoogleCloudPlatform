# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function

import os
from pathlib import Path

import nox

# Proposed TEST_CONFIG.
# You can have a file `testconfig` or something and it will be injected into
# the generated noxfile.py.
TEST_CONFIG = {
    'use_multi_project': True,
    'ignored_versions': ["2.7"],
    'other_configs': ['other value1', 'other value2'],
}


# This is a fixed dictionary in the template.
# Currently I use my personal project for prototyping.
PROJECT_TABLE = {
    'python2.7': 'python-docs-samples-tests',
    'python3.6': 'python-docs-samples-tests',
    'python3.7': 'tmatsuo-test',
    'python3.8': 'python-docs-samples-tests',
}


def get_pytest_env_vars():
    """Returns a dict for pytest invocation.

    Currently only use cse is to override env vars for test project.
    """
    ret = {}

    if TEST_CONFIG.get('use_multi_project', False):
        # KOKORO_JOB_NAME is in the following format:
        # cloud-devrel/python-docs-samples/pythonN.M/BUILD_TYPE(e.g: continuous)
        # Currently we only look at the python version.
        kokoro_job_name = os.environ.get('KOKORO_JOB_NAME')
        if kokoro_job_name:
            parts = kokoro_job_name.split('/')
            if len(parts) >= 2:
                # build_type = parts[-1]
                python_version = parts[-2]

                if python_version in PROJECT_TABLE:
                    ret['GOOGLE_CLOUD_PROJECT'] = PROJECT_TABLE[python_version]
                    ret['GCLOUD_PROJECT'] = PROJECT_TABLE[python_version]

    return ret


# DO NOT EDIT - automatically generated.
# All versions used to tested samples.
ALL_VERSIONS = ["2.7", "3.6", "3.7", "3.8"]

# Any default versions that should be ignored.
IGNORED_VERSIONS = TEST_CONFIG.get('ignored_versions', {})

TESTED_VERSIONS = sorted([v for v in ALL_VERSIONS if v not in IGNORED_VERSIONS])

#
# Style Checks
#


# Ignore I202 "Additional newline in a section of imports." to accommodate
# region tags in import blocks. Since we specify an explicit ignore, we also
# have to explicitly ignore the list of default ignores:
# `E121,E123,E126,E226,E24,E704,W503,W504` as shown by `flake8 --help`.
def _determine_local_import_names(start_dir):
    """Determines all import names that should be considered "local".

    This is used when running the linter to insure that import order is
    properly checked.
    """
    file_ext_pairs = [os.path.splitext(path) for path in os.listdir(start_dir)]
    return [
        basename
        for basename, extension in file_ext_pairs
        if extension == ".py"
        or os.path.isdir(os.path.join(start_dir, basename))
        and basename not in ("__pycache__")
    ]


FLAKE8_COMMON_ARGS = [
    "--show-source",
    "--builtin=gettext",
    "--max-complexity=20",
    "--import-order-style=google",
    "--exclude=.nox,.cache,env,lib,generated_pb2,*_pb2.py,*_pb2_grpc.py",
    "--ignore=E121,E123,E126,E203,E226,E24,E266,E501,E704,W503,W504,I100,I201,I202",
    "--max-line-length=88",
]


@nox.session
def lint(session):
    session.install("flake8", "flake8-import-order")

    local_names = _determine_local_import_names(".")
    args = FLAKE8_COMMON_ARGS + [
        "--application-import-names",
        ",".join(local_names),
        ".",
    ]
    session.run("flake8", *args)


#
# Sample Tests
#


PYTEST_COMMON_ARGS = ["--junitxml=sponge_log.xml"]


def _session_tests(session, post_install=None):
    """Runs py.test for a particular project."""
    if os.path.exists("requirements.txt"):
        session.install("-r", "requirements.txt")

    if os.path.exists("requirements-test.txt"):
        session.install("-r", "requirements-test.txt")

    if post_install:
        post_install(session)

    session.run(
        "pytest",
        *(PYTEST_COMMON_ARGS + session.posargs),
        # Pytest will return 5 when no tests are collected. This can happen
        # on travis where slow and flaky tests are excluded.
        # See http://doc.pytest.org/en/latest/_modules/_pytest/main.html
        success_codes=[0, 5],
        env=get_pytest_env_vars()
    )


@nox.session(python=ALL_VERSIONS)
def py(session):
    """Runs py.test for a sample using the specified version of Python."""
    if session.python in TESTED_VERSIONS:
        _session_tests(session)
    else:
        print("SKIPPED: {} tests are disabled for this sample.".format(session.python))


#
# Readmegen
#


def _get_repo_root():
    """ Returns the root folder of the project. """
    # Get root of this repository. Assume we don't have directories nested deeper than 10 items.
    p = Path(os.getcwd())
    for i in range(10):
        if p is None:
            break
        if Path(p / ".git").exists():
            return str(p)
        p = p.parent
    raise Exception("Unable to detect repository root.")


GENERATED_READMES = sorted([x for x in Path(".").rglob("*.rst.in")])


@nox.session
@nox.parametrize("path", GENERATED_READMES)
def readmegen(session, path):
    """(Re-)generates the readme for a sample."""
    session.install("jinja2", "pyyaml")
    dir_ = os.path.dirname(path)

    if os.path.exists(os.path.join(dir_, "requirements.txt")):
        session.install("-r", os.path.join(dir_, "requirements.txt"))

    in_file = os.path.join(dir_, "README.rst.in")
    session.run(
        "python", _get_repo_root() + "/scripts/readme-gen/readme_gen.py", in_file
    )
