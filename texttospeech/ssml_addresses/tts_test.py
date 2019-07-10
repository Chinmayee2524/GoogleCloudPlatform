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

from tts import text_to_ssml
from tts import ssml_to_audio

import filecmp
import os


def test_text_to_ssml(capsys):

    # Assert plaintext converted to SSML
    input_text = 'resources/example.txt'
    tested_ssml = text_to_ssml(input_text)
    expected_ssml = '<speak>123 Street Ln, Small Town, IL 12345 USA\n' \
                    '<break time="2s"/>1 Jenny St &amp; Number St,' \
                    ' Tutone City, CA 86753\n' \
                    '<break time="2s"/>1 Piazza del Fibonacci,' \
                    ' 12358 Pisa, Italy\n<break time="2s"/></speak>'
    assert expected_ssml == tested_ssml


def test_ssml_to_audio(capsys):

    input_ssml = '<speak>123 Street Ln, Small Town, IL 12345 USA\n' \
                 '<break time="2s"/>1 Jenny St &amp; Number St,' \
                 ' Tutone City, CA 86753\n' \
                 '<break time="2s"/>1 Piazza del Fibonacci,' \
                 ' 12358 Pisa, Italy\n<break time="2s"/></speak>'

    # Assert audio file generated
    ssml_to_audio(input_ssml, 'test_example.mp3')
    assert os.path.isfile('test_example.mp3')

    # Assert audio file generated correctly
    assert filecmp.cmp('test_example.mp3',
                       'resources/expected_example.mp3',
                       shallow=True)
    out, err = capsys.readouterr()

    # Assert success message printed
    assert "Audio content written to file test_example.mp3" in out

    # Assert that no mp3 file generated if given empty SSML input
    # NOTE to work correctly, directory must not already contain a file
    # named 'non_existent_input.mp3'
    ssml_to_audio(None, 'non_existent_input.mp3')
    assert os.path.isfile('non_existent_input.mp3') is False
