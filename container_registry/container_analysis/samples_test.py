#!/bin/python
# Copyright 2018 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from os import environ
from time import sleep, time

from google.api_core.exceptions import InvalidArgument
from google.api_core.exceptions import NotFound
from google.cloud.devtools.containeranalysis_v1alpha1.proto.\
    containeranalysis_pb2 import Occurrence
from google.cloud.devtools.containeranalysis_v1alpha1.proto.\
    package_vulnerability_pb2 import VulnerabilityType
from google.cloud.pubsub import SubscriberClient

import samples

PROJECT_ID = environ['GCLOUD_PROJECT']
SLEEP_TIME = 1
TRY_LIMIT = 20


class TestContainerAnalysisSamples:

    def setup_method(self, test_method):
        print("SETUP " + test_method.__name__)
        timestamp = str(int(time()))
        self.note_id = "note-" + timestamp + test_method.__name__
        self.image_url = "www." + timestamp + test_method.__name__ + ".com"
        self.note_obj = samples.create_note(self.note_id, PROJECT_ID)

    def teardown_method(self, test_method):
        print("TEAR DOWN " + test_method.__name__)
        try:
            samples.delete_note(self.note_id, PROJECT_ID)
        except NotFound:
            pass

    def test_create_note(self):
        new_note = samples.get_note(self.note_id, PROJECT_ID)
        assert new_note.name == self.note_obj.name

    def test_delete_note(self):
        samples.delete_note(self.note_id, PROJECT_ID)
        try:
            samples.get_note(self.note_obj, PROJECT_ID)
        except InvalidArgument:
            pass
        else:
            # didn't raise exception we expected
            assert (False)

    def test_update_note(self):
        description = "updated"
        self.note_obj.short_description = description
        samples.update_note(self.note_obj, self.note_id, PROJECT_ID)

        updated = samples.get_note(self.note_id, PROJECT_ID)
        assert updated.short_description == description

    def test_create_occurrence(self):
        created = samples.create_occurrence(self.image_url,
                                            self.note_id,
                                            PROJECT_ID)
        retrieved = samples.get_occurrence(created.name)
        assert created.name == retrieved.name
        # clean up
        samples.delete_occurrence(created.name)

    def test_delete_occurrence(self):
        created = samples.create_occurrence(self.image_url,
                                            self.note_id,
                                            PROJECT_ID)
        samples.delete_occurrence(created.name)
        try:
            samples.get_occurrence(created.name)
        except NotFound:
            pass
        else:
            # didn't raise exception we expected
            assert False

    def test_update_occurrence(self):
        new_type = "newType"
        created = samples.create_occurrence(self.image_url,
                                            self.note_id,
                                            PROJECT_ID)

        vul_details = VulnerabilityType.VulnerabilityDetails()
        vul_details.type = new_type
        update_prototype = Occurrence(note_name=created.note_name,
                                      resource_url=self.image_url,
                                      vulnerability_details=vul_details)

        samples.update_occurrence(update_prototype, created.name)
        retrieved = samples.get_occurrence(created.name)
        assert retrieved.vulnerability_details.type == new_type
        # clean up
        samples.delete_occurrence(created.name)

    def test_occurrences_for_image(self):
        origCount = samples.get_occurrences_for_image(self.image_url,
                                                      PROJECT_ID)
        occ = samples.create_occurrence(self.image_url, self.note_id,
                                        PROJECT_ID)
        newCount = 0
        tries = 0
        while newCount != 1 and tries < TRY_LIMIT:
            tries += 1
            newCount = samples.get_occurrences_for_image(self.image_url,
                                                         PROJECT_ID)
            sleep(SLEEP_TIME)
        assert newCount == 1
        assert origCount == 0
        # clean up
        samples.delete_occurrence(occ.name)

    def test_occurrences_for_note(self):
        origCount = samples.get_occurrences_for_note(self.note_id,
                                                     PROJECT_ID)
        occ = samples.create_occurrence(self.image_url,
                                        self.note_id,
                                        PROJECT_ID)
        newCount = 0
        tries = 0
        while newCount != 1 and tries < TRY_LIMIT:
            tries += 1
            newCount = samples.get_occurrences_for_note(self.note_id,
                                                        PROJECT_ID)
            sleep(SLEEP_TIME)
        assert newCount == 1
        assert origCount == 0
        # clean up
        samples.delete_occurrence(occ.name)

    def test_pubsub(self):
        client = SubscriberClient()
        subscription_id = "drydockOccurrences"
        subscription_name = client.subscription_path(PROJECT_ID,
                                                     subscription_id)

        samples.create_occurrence_subscription(subscription_id, PROJECT_ID)
        receiver = samples.MessageReceiver()
        client.subscribe(subscription_name, receiver.pubsub_callback)

        # sleep so any messages in the queue can go through
        # and be counted before we start the test
        sleep(SLEEP_TIME*TRY_LIMIT)
        # set the initial state of our counter
        startVal = receiver.msg_count + 1
        # test adding 3 more occurrences
        for i in range(startVal, startVal+3):
            occ = samples.create_occurrence(self.image_url,
                                            self.note_id,
                                            PROJECT_ID)
            print("CREATED: " + occ.name)
            tries = 0
            newCount = receiver.msg_count
            while newCount != i and tries < TRY_LIMIT:
                tries += 1
                sleep(SLEEP_TIME)
                newCount = receiver.msg_count
            print(str(receiver.msg_count) + " : " + str(i))
            assert i == receiver.msg_count
            samples.delete_occurrence(occ.name)
        # clean up
        client.delete_subscription(subscription_name)
