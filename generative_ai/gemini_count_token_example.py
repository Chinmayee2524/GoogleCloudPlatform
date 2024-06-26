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


def generate_text(project_id: str, location: str) -> str:
    # [START generativeaionvertexai_gemini_token_count]
    import vertexai

    from vertexai.generative_models import GenerativeModel

    # Initialize Vertex AI
    vertexai.init(project=project_id, location=location)

    # Load the model
    model = GenerativeModel(model_name="gemini-1.0-pro-002")

    # prompt tokens count
    print(model.count_tokens("why is sky blue?"))

    # Load example images
    response = model.generate_content("why is sky blue?")

    # response tokens count
    print(response._raw_response.usage_metadata)
    # [END generativeaionvertexai_gemini_token_count]
    return response.text
