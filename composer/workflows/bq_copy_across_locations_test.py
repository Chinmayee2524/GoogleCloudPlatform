# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from airflow import models
import os


def test_dag_import():
    """Test that the DAG file can be successfully imported.

    This tests that the DAG can be parsed, but does not run it in an Airflow
    environment. This is a recommended sanity check by the official Airflow
    docs: https://airflow.incubator.apache.org/tutorial.html#testing
    """
    example_file_path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        'bq_copy_eu_to_us_sample.csv')
    models.Variable.set('table_list_file_path', example_file_path)
    models.Variable.set('gcs_source_bucket', 'example-project')
    models.Variable.set('gcs_dest_bucket', 'us-central1-f')