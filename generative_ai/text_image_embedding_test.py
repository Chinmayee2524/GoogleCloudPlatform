# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import backoff
from google.api_core.exceptions import ResourceExhausted

import text_image_embedding


@backoff.on_exception(backoff.expo, ResourceExhausted, max_time=10)
def test_text_embedding() -> None:
    images = text_image_embedding.generate_image_from_text_and_image(
        prompt="Ancient yellowed paper scroll"
    )
    assert images[0] is not None
