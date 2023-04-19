#!/usr/bin/env python
# Copyright 2023 Google LLC
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
#
# All Rights Reserved.

from long_audio_quickstart import synthesize_long_audio
import uuid
import google.auth
from google.cloud import storage
import pytest

@pytest.fixture(scope="module")
def test_bucket():
    """Yields a bucket that is deleted after the test completes."""
    bucket = None
    while bucket is None or bucket.exists():
        bucket_name = f"tts-long-audio-test-{uuid.uuid4()}"
        bucket = storage.Client().bucket(bucket_name)
    bucket.create()
    yield bucket
    bucket.delete(force=True)

def test_synthesize_long_audio(capsys, test_bucket):
    PROJECT_NUMBER = os.environ["GOOGLE_CLOUD_PROJECT_NUMBER"]
    parent = "projects/" + PROJECT_NUMBER + "/locations/us-central1"

    file_name = "fake_file.wav"
    output_gcs_uri = "gs://" test_bucket.name + "/" + file_name

    assert synthesize_long_audio("some text to synthesize", "en-US", "en-US-Standard-A", parent, output_gcs_uri)
