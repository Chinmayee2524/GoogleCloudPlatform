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

from __future__ import annotations

import logging

import apache_beam as beam
from apache_beam.ml.inference.base import PredictionResult
from apache_beam.ml.inference.base import RunInference
from apache_beam.ml.inference.pytorch_inference import make_tensor_model_fn
from apache_beam.ml.inference.pytorch_inference import PytorchModelHandlerTensor
from apache_beam.options.pipeline_options import PipelineOptions
import torch
from transformers import AutoConfig
from transformers import AutoModelForSeq2SeqLM
from transformers import AutoTokenizer

MAX_RESPONSE_TOKENS = 256


def encode_tokens(input_text: str, tokenizer: AutoTokenizer) -> torch.Tensor:
    return tokenizer(input_text, return_tensors="pt").input_ids[0]


def decode_tokens(result: PredictionResult, tokenizer: AutoTokenizer) -> str:
    output_tokens = result.inference
    return tokenizer.decode(output_tokens, skip_special_tokens=True)


def run(
    model_name: str,
    state_dict_path: str,
    beam_options: PipelineOptions | None = None,
) -> None:
    model_handler = PytorchModelHandlerTensor(
        state_dict_path=state_dict_path,
        model_class=AutoModelForSeq2SeqLM.from_config,
        model_params={"config": AutoConfig.from_pretrained(model_name)},
        inference_fn=make_tensor_model_fn("generate"),
    )

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    with beam.Pipeline(options=beam_options) as pipeline:
        _ = (
            pipeline
            | beam.Create(["Hello!"])
            | "Encode tokens" >> beam.Map(encode_tokens, tokenizer)
            | "RunInference"
            >> RunInference(
                model_handler,
                inference_args={"max_new_tokens": MAX_RESPONSE_TOKENS},
            )
            | "Decode tokens" >> beam.Map(decode_tokens, tokenizer)
            | beam.Map(logging.info)
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--state-dict-path", required=True)
    args, beam_args = parser.parse_known_args()

    logging.getLogger().setLevel(logging.INFO)
    beam_options = PipelineOptions(
        beam_args,
        save_main_session=True,
        streaming=True,
        requirements_file="requirements.txt",
    )
    run(
        state_dict_path=args.state_dict_path,
        model_name=args.model_name,
        beam_options=beam_options,
    )
