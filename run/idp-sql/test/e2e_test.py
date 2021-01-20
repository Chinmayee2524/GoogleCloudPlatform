# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This test creates a Cloud SQL instance, a Cloud Storage bucket, associated
# secrets, and deploys a Django service

import os
import subprocess

#import firebase_admin
import pytest
import requests
from firebase_admin import auth

# default_app = firebase_admin.initialize_app()


GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", None)
if not GOOGLE_CLOUD_PROJECT:
    raise Exception("'GOOGLE_CLOUD_PROJECT' env var not found")

SERVICE_NAME = os.environ.get("SERVICE_NAME", None)
if not SERVICE_NAME:
    print("'SERVICE_NAME' envvar not found. Defaulting to 'idp-sql'")
    SERVICE_NAME = "idp-sql"

SAMPLE_VERSION = os.environ.get("SAMPLE_VERSION", None)

REGION = "us-central1"
PLATFORM = "managed"

# Retreieve Cloud SQL test config
POSTGRES_INSTANCE = os.environ.get("POSTGRES_INSTANCE", None)
if not POSTGRES_INSTANCE:
    raise Exception("'POSTGRES_INSTANCE' env var not found")

POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", None)
if not POSTGRES_PASSWORD:
    raise Exception("'POSTGRES_PASSWORD' env var not found")

# Firebase key to create Id Tokens
IDP_KEY = os.environ.get("IDP_KEY", None)
if not IDP_KEY:
    raise Exception("'IDP_KEY' env var not found")


@pytest.fixture
def deployed_service() -> str:
    substitutions = [
        f"_SERVICE={SERVICE_NAME},"
        f"_PLATFORM={PLATFORM},"
        f"_REGION={REGION},"
        f"_DB_PASSWORD={POSTGRES_PASSWORD},"
        f"_CLOUD_SQL_CONNECTION_NAME={POSTGRES_INSTANCE},"
    ]
    if SAMPLE_VERSION:
        substitutions.append(f"_SAMPLE_VERSION={SAMPLE_VERSION}")

    subprocess.run(
        [
            "gcloud",
            "builds",
            "submit",
            "--project",
            GOOGLE_CLOUD_PROJECT,
            "--config",
            "./test/e2e_test_setup.yaml",
            "--substitutions",
        ]
        + substitutions,
        check=True,
    )

    service_url = (
        subprocess.run(
            [
                "gcloud",
                "run",
                "services",
                "describe",
                SERVICE_NAME,
                "--project",
                GOOGLE_CLOUD_PROJECT,
                "--platform",
                PLATFORM,
                "--region",
                REGION,
                "--format",
                "value(status.url)",
            ],
            stdout=subprocess.PIPE,
            check=True,
        )
        .stdout.strip()
        .decode()
    )

    yield service_url

    # Cleanup

    substitutions = [
        f"_SERVICE={SERVICE_NAME}," f"_PLATFORM={PLATFORM}," f"_REGION={REGION},"
    ]
    if SAMPLE_VERSION:
        substitutions.append(f"_SAMPLE_VERSION={SAMPLE_VERSION}")

    subprocess.run(
        [
            "gcloud",
            "builds",
            "submit",
            "--project",
            GOOGLE_CLOUD_PROJECT,
            "--config",
            "./test/e2e_test_cleanup.yaml",
            "--substitutions",
        ]
        + substitutions,
        check=True,
    )


@pytest.fixture
def jwt_token() -> str:
    custom_token = auth.create_custom_token("a-user-id").decode("UTF-8")
    response = requests.post(
        f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key=${IDP_KEY}",
        json={"token": custom_token, "returnSecureToken": True},
    )
    tokens = response.json()
    id_token = tokens["idToken"]
    yield id_token

    # no cleanup required


def test_end_to_end(jwt_token: str, deployed_service: str) -> None:
    token = jwt_token
    service_url = deployed_service

    client = requests.session()

    # Can successfully make a request
    response = client.get(service_url, headers=headers)
    body = response.text

    assert response.status_code == 200
    # TODO(glasnt) more checks
    # * can make post with token
    # * cannot make post with bad token
    # * cannot make post with no token
