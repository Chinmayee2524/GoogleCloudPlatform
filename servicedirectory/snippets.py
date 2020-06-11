#!/usr/bin/env python

# Copyright 2020 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from google.cloud import servicedirectory_v1beta1


def create_namespace(project_id, location_id, namespace_id):
  """Creates a namespace in the given location."""

  client = servicedirectory_v1beta1.RegistrationServiceClient()

  namespace = servicedirectory_v1beta1.Namespace(
      name='projects/{0}/locations/{1}/namespaces/{2}'.format(
          project_id, location_id, namespace_id))

  response = client.create_namespace(
      parent='projects/{0}/locations/{1}'.format(project_id, location_id),
      namespace=namespace,
      namespace_id=namespace_id,
  )

  print('Created namespace {0}.'.format(response.name))

  return response


def delete_namespace(project_id, location_id, namespace_id):
  """Deletes a namespace in the given location."""

  client = servicedirectory_v1beta1.RegistrationServiceClient()

  namespace_name = 'projects/{0}/locations/{1}/namespaces/{2}'.format(
      project_id, location_id, namespace_id)

  client.delete_namespace(name=namespace_name)

  print('Deleted namespace {0}.'.format(namespace_name))


def create_service(project_id, location_id, namespace_id, service_id):
  """Creates a service in the given namespace."""

  client = servicedirectory_v1beta1.RegistrationServiceClient()

  service = servicedirectory_v1beta1.Service(
      name='projects/{0}/locations/{1}/namespaces/{2}/services/{3}'.format(
          project_id, location_id, namespace_id, service_id))

  response = client.create_service(
      parent='projects/{0}/locations/{1}/namespaces/{2}'.format(
          project_id, location_id, namespace_id),
      service=service,
      service_id=service_id,
  )

  print('Created service {0}.'.format(response.name))

  return response


def delete_service(project_id, location_id, namespace_id, service_id):
  """Deletes a service in the given namespace."""

  client = servicedirectory_v1beta1.RegistrationServiceClient()

  service_name = 'projects/{0}/locations/{1}/namespaces/{2}/services/{3}'.format(
      project_id, location_id, namespace_id, service_id)

  client.delete_service(name=service_name)

  print('Deleted service {0}.'.format(service_name))


def resolve_service(project_id, location_id, namespace_id, service_id):
  """Resolves a service in the given namespace."""

  client = servicedirectory_v1beta1.LookupServiceClient()

  request = servicedirectory_v1beta1.ResolveServiceRequest(
      name='projects/{0}/locations/{1}/namespaces/{2}/services/{3}'.format(
          project_id, location_id, namespace_id, service_id))

  response = client.resolve_service(request=request)

  print('Endpoints found:')
  for endpoint in response.service.endpoints:
    print('{0} -- {1}:{2}'.format(endpoint.name, endpoint.address,
                                  endpoint.port))

  return response


def create_endpoint(project_id, location_id, namespace_id, service_id,
                    endpoint_id, address, port):
  """Creates a endpoint in the given service."""

  client = servicedirectory_v1beta1.RegistrationServiceClient()

  endpoint = servicedirectory_v1beta1.Endpoint(
      name='projects/{0}/locations/{1}/namespaces/{2}/services/{3}/endpoints/{4}'
      .format(project_id, location_id, namespace_id, service_id, endpoint_id),
      address=address,
      port=port)

  response = client.create_endpoint(
      parent='projects/{0}/locations/{1}/namespaces/{2}/services/{3}'.format(
          project_id, location_id, namespace_id, service_id),
      endpoint=endpoint,
      endpoint_id=endpoint_id,
    )

  print('Created endpoint {0}.'.format(response.name))

  return response


def delete_endpoint(project_id, location_id, namespace_id, service_id,
                    endpoint_id):
  """Deletes a endpoin in the given service."""

  client = servicedirectory_v1beta1.RegistrationServiceClient()

  endpoint_name = 'projects/{0}/locations/{1}/namespaces/{2}/services/{3}/endpoints/{4}'.format(
      project_id, location_id, namespace_id, service_id, endpoint_id)

  client.delete_endpoint(name=endpoint_name)

  print('Deleted endpoint {0}.'.format(endpoint_name))
