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

# [START generativeai_sdk_embedding]
from google.cloud.aiplatform.private_preview.language_models import TextEmbeddingModel


def text_embedding():
  """Text embedding with a Large Language Model."""
  model = TextEmbeddingModel.from_pretrained("google/embedding-gecko-001")
  embeddings = model.get_embeddings(["What is life?"])
  for embedding in embeddings:
      vector = embedding.values
      print(f'Length of Embedding Vector: {len(vector)}')
# [END generativeai_sdk_embedding]
  return vector


if __name__ == "__main__":
    text_embedding()
