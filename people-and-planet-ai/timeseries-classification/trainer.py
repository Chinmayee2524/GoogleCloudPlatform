# Copyright 2021 Google LLC
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

from functools import reduce
import logging
import os
from typing import Any, Dict, Tuple

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.layers.experimental import preprocessing


INPUTS_SPEC = {
    "distance_from_port": tf.TensorSpec(shape=(None, 1), dtype=tf.float32),
    "speed": tf.TensorSpec(shape=(None, 1), dtype=tf.float32),
    "course": tf.TensorSpec(shape=(None, 1), dtype=tf.float32),
    "lat": tf.TensorSpec(shape=(None, 1), dtype=tf.float32),
    "lon": tf.TensorSpec(shape=(None, 1), dtype=tf.float32),
}

OUTPUTS_SPEC = {
    "is_fishing": tf.TensorSpec(shape=(None, 1), dtype=tf.float32),
}

PADDING = 24


def validated(
    tensor_dict: Dict[str, tf.Tensor],
    spec_dict: Dict[str, tf.TypeSpec],
) -> Dict[str, tf.Tensor]:
    for field, spec in spec_dict.items():
        if field not in tensor_dict:
            raise KeyError(
                f"missing field '{field}', got={tensor_dict.keys()}, expected={spec_dict.keys()}"
            )
        if not spec.dtype.is_compatible_with(tensor_dict[field].dtype):
            raise TypeError(
                f"incompatible type in '{field}', got={tensor_dict[field].dtype}, expected={spec.dtype}"
            )
        if not spec.shape.is_compatible_with(tensor_dict[field].shape):
            raise ValueError(
                f"incompatible shape in '{field}', got={tensor_dict[field].shape}, expected={spec.shape}"
            )
    return tensor_dict


def serialize(value_dict: Dict[str, Any]) -> bytes:
    spec_dict = {**INPUTS_SPEC, **OUTPUTS_SPEC}
    tensor_dict = {
        field: tf.convert_to_tensor(value, spec_dict[field].dtype)
        for field, value in value_dict.items()
    }
    validated_tensor_dict = validated(tensor_dict, spec_dict)

    example = tf.train.Example(
        features=tf.train.Features(
            feature={
                field: tf.train.Feature(
                    bytes_list=tf.train.BytesList(
                        value=[tf.io.serialize_tensor(value).numpy()]
                    )
                )
                for field, value in validated_tensor_dict.items()
            }
        )
    )
    return example.SerializeToString()


def deserialize(
    serialized_example: bytes,
) -> Tuple[Dict[str, tf.Tensor], Dict[str, tf.Tensor]]:
    features = {
        field: tf.io.FixedLenFeature(shape=(), dtype=tf.string)
        for field in [*INPUTS_SPEC.keys(), *OUTPUTS_SPEC.keys()]
    }
    example = tf.io.parse_example(serialized_example, features)

    def parse_tensor(bytes_value: bytes, spec: tf.TypeSpec) -> tf.Tensor:
        tensor = tf.io.parse_tensor(bytes_value, spec.dtype)
        tensor.set_shape(spec.shape)
        return tensor

    def parse_features(spec_dict: Dict[str, tf.TypeSpec]) -> Dict[str, tf.Tensor]:
        tensor_dict = {
            field: parse_tensor(bytes_value, spec_dict[field])
            for field, bytes_value in example.items()
            if field in spec_dict
        }
        return validated(tensor_dict, spec_dict)

    return parse_features(INPUTS_SPEC), parse_features(OUTPUTS_SPEC)


def create_dataset(data_dir: str, batch_size: int) -> tf.data.Dataset:
    file_names = tf.io.gfile.glob(f"{data_dir}/*")
    return (
        tf.data.TFRecordDataset(file_names, compression_type="GZIP")
        .map(deserialize, num_parallel_calls=tf.data.AUTOTUNE)
        .shuffle(batch_size * 128)
        .batch(batch_size)
        .prefetch(tf.data.AUTOTUNE)
    )


def create_model(train_dataset: tf.data.Dataset) -> keras.Model:
    input_layers = {
        name: keras.layers.Input(shape=spec.shape, dtype=spec.dtype, name=name)
        for name, spec in INPUTS_SPEC.items()
    }

    def normalize(name: str):
        layer = preprocessing.Normalization(name=f"{name}_normalized")
        layer.adapt(train_dataset.map(lambda inputs, outputs: inputs[name]))
        return layer(input_layers[name])

    def geo_point(lat_name: str, lon_name: str):
        # We transform each (lat, lon) pair into a 3D point in the unit sphere.
        #   https://en.wikipedia.org/wiki/Spherical_coordinate_system#Cartesian_coordinates
        class GeoPoint(keras.layers.Layer):
            def call(self, latlon):
                lat, lon = latlon
                x = tf.cos(lon) * tf.sin(lat)
                y = tf.sin(lon) * tf.sin(lat)
                z = tf.cos(lat)
                return tf.concat([x, y, z], axis=-1)

        lat_lon_input_layers = (input_layers[lat_name], input_layers[lon_name])
        return GeoPoint(name=f"{lat_name}_{lon_name}")(lat_lon_input_layers)

    def sequential_layers(first_layer, *layers) -> keras.layers.Layer:
        return reduce(lambda layer, result: result(layer), layers, first_layer)

    preprocessed_inputs = [
        normalize("distance_from_port"),
        normalize("speed"),
        normalize("course"),
        geo_point("lat", "lon"),
    ]

    output_layers = {
        "is_fishing": sequential_layers(
            keras.layers.concatenate(preprocessed_inputs, name="deep_layers"),
            keras.layers.Conv1D(
                filters=32,
                kernel_size=PADDING + 1,
                data_format="channels_last",
                activation="relu",
            ),
            keras.layers.Dense(16, activation="relu"),
            keras.layers.Dense(1, activation="sigmoid", name="is_fishing"),
        )
    }
    return keras.Model(input_layers, output_layers)


def run(
    train_data_dir: str,
    eval_data_dir: str,
    train_steps: int,
    eval_steps: int,
    batch_size: int,
    model_dir: str,
    checkpoint_dir: str,
    tensorboard_dir: str,
) -> None:

    # For this sample we are using a mirrored distribution strategy,
    # which consists of a single machine with multiple GPUs.
    #   https://blog.tensorflow.org/2020/12/getting-started-with-distributed-tensorflow-on-gcp.html
    distributed_strategy = tf.distribute.MirroredStrategy()

    # Create the training and evaluation datasets from the TFRecord files.
    logging.info("Creating datasets")
    total_batch_size = batch_size * distributed_strategy.num_replicas_in_sync
    train_dataset = create_dataset(train_data_dir, total_batch_size)
    eval_dataset = create_dataset(eval_data_dir, total_batch_size)

    # Create and compile the model inside the distribution strategy scope.
    with distributed_strategy.scope():
        logging.info("Creating the model")
        model = create_model(train_dataset)

        logging.info("Compiling the model")
        model.compile(
            optimizer="adam",  #                           https://keras.io/api/optimizers
            loss={"is_fishing": "binary_crossentropy"},  # https://keras.io/api/losses
            metrics={"is_fishing": ["accuracy"]},  #       https://keras.io/api/metrics
        )

    # Train the model.
    logging.info("Training the model")
    model.fit(
        train_dataset.repeat(),
        steps_per_epoch=train_steps,
        validation_data=eval_dataset.repeat(),
        validation_steps=eval_steps,
        callbacks=[
            keras.callbacks.TensorBoard(tensorboard_dir, update_freq="batch"),
            keras.callbacks.ModelCheckpoint(
                filepath=checkpoint_dir + "/{epoch}",
                save_best_only=True,  # Only save a model if `val_loss` has improved.
                monitor="val_loss",
                verbose=1,
            ),
        ],
    )

    # Save the trained model.
    logging.info(f"Saving the model: {model_dir}")
    model.save(model_dir)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--train-data-dir", required=True)
    parser.add_argument("--eval-data-dir", required=True)
    parser.add_argument("--train-steps", type=int, required=True)
    parser.add_argument("--eval-steps", type=int, required=True)
    parser.add_argument("--batch-size", type=int, required=True)
    parser.add_argument(
        "--model-dir",
        default=os.environ.get("AIP_MODEL_DIR", "model"),
    )
    parser.add_argument(
        "--checkpoint-dir",
        default=os.environ.get("AIP_CHECKPOINT_DIR", "checkpoints"),
    )
    parser.add_argument(
        "--tensorboard-dir",
        default=os.environ.get("AIP_TENSORBOARD_LOG_DIR", "tensorboard"),
    )
    args = parser.parse_args()

    logging.getLogger().setLevel(logging.INFO)
    run(
        train_data_dir=args.train_data_dir,
        eval_data_dir=args.eval_data_dir,
        train_steps=args.train_steps,
        eval_steps=args.eval_steps,
        batch_size=args.batch_size,
        model_dir=args.model_dir,
        checkpoint_dir=args.checkpoint_dir,
        tensorboard_dir=args.tensorboard_dir,
    )
