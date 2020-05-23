#!/usr/bin/env bash
# Copyright 2020 Google LLC
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

# trampoline_v2.sh
#
# This script does 3 things.
#
# 1. Prepare the Docker image for the test
# 2. Run the Docker with appropriate flags to run the test
# 3. Upload the newly built Docker image
#
# in a way that is somewhat compatible with trampoline_v1.
#
# To run this script, first download few files from gcs to /dev/shm.
# (/dev/shm is passed into the container as KOKORO_GFILE_DIR).
#
# gsutil cp gs://cloud-devrel-kokoro-resources/python-docs-samples/secrets_viewer_service_account.json /dev/shm
# gsutil cp gs://cloud-devrel-kokoro-resources/python-docs-samples/automl_secrets.txt /dev/shm
#
# Then run the script.
# .kokoro/trampoline_v2.sh
#
# You can optionally change these environment variables:
#
# TRAMPOLINE_IMAGE: The docker image to use.
# TRAMPOLINE_IMAGE_SOURCE: The location of the Dockerfile.
# TRAMPOLINE_IMAGE_UPLOAD:
#     (true|false): Whether to upload the Docker image after the
#                   successful builds.
# TRAMPOLINE_BUILD_FILE: The script to run in the docker container.
#
# Potentially there are some repo specific envvars in .trampolinerc in
# the project root.


set -euo pipefail

if command -v tput >/dev/null && [[ -n "${TERM:-}" ]]; then
  readonly IO_COLOR_RED="$(tput setaf 1)"
  readonly IO_COLOR_GREEN="$(tput setaf 2)"
  readonly IO_COLOR_YELLOW="$(tput setaf 3)"
  readonly IO_COLOR_RESET="$(tput sgr0)"
else
  readonly IO_COLOR_RED=""
  readonly IO_COLOR_GREEN=""
  readonly IO_COLOR_YELLOW=""
  readonly IO_COLOR_RESET=""
fi

# Logs a message using the given color. The first argument must be one
# of the IO_COLOR_* variables defined above, such as
# "${IO_COLOR_YELLOW}". The remaining arguments will be logged in the
# given color. The log message will also have an RFC-3339 timestamp
# prepended (in UTC). You can disable the color output by setting
# TERM=vt100.
function log_impl() {
    local color="$1"
    shift
    local timestamp="$(date -u "+%Y-%m-%dT%H:%M:%SZ")"
    echo "================================================================"
    echo "${color}${timestamp}:" "$@" "${IO_COLOR_RESET}"
    echo "================================================================"
}

# Logs the given message with normal coloring and a timestamp.
function log() {
  log_impl "${IO_COLOR_RESET}" "$@"
}

# Logs the given message in green with a timestamp.
function log_green() {
  log_impl "${IO_COLOR_GREEN}" "$@"
}

# Logs the given message in yellow with a timestamp.
function log_yellow() {
  log_impl "${IO_COLOR_YELLOW}" "$@"
}

# Logs the given message in red with a timestamp.
function log_red() {
  log_impl "${IO_COLOR_RED}" "$@"
}

readonly tmpdir=$(mktemp -d -t ci-XXXXXXXX)
readonly tmphome="${tmpdir}/h"
mkdir -p "${tmphome}"

function cleanup() {
    rm -rf "${tmpdir}"
}
trap cleanup EXIT

function repo_root() {
    local dir="$1"
    while [[ ! -d "${dir}/.git" ]]; do
	dir="$(dirname "$dir")"
    done
    echo "${dir}"
}

PROGRAM_PATH="$(realpath "$0")"
PROGRAM_DIR="$(dirname "${PROGRAM_PATH}")"
PROJECT_ROOT="$(repo_root "${PROGRAM_DIR}")"

RUNNING_IN_CI="false"

if [[ -n "${KOKORO_GFILE_DIR:-}" ]]; then
    # descriptive env var for indicating it's on CI.
    RUNNING_IN_CI="true"

    # Now we're re-using the trampoline service account.
    # Potentially we can pass down this key into Docker for
    # bootstrapping secret.
    SERVICE_ACCOUNT_KEY_FILE="${KOKORO_GFILE_DIR}/kokoro-trampoline.service-account.json"

    mkdir -p "${tmpdir}/gcloud"
    gcloud_config_dir="${tmpdir}/gcloud"

    log "Using isolated gcloud config: ${gcloud_config_dir}."
    export CLOUDSDK_CONFIG="${gcloud_config_dir}"

    log "Using ${SERVICE_ACCOUNT_KEY_FILE} for authentication."
    gcloud auth activate-service-account \
	   --key-file "${SERVICE_ACCOUNT_KEY_FILE}"
    gcloud auth configure-docker --quiet
fi

log_yellow "Changing to the project root: ${PROJECT_ROOT}."
cd "${PROJECT_ROOT}"

required_envvars=(
    # The basic trampoline configurations.
    "TRAMPOLINE_IMAGE"
    "TRAMPOLINE_BUILD_FILE"
)

pass_down_envvars=(
    # Default empty list.
)

if [[ -f "${PROJECT_ROOT}/.trampolinerc" ]]; then
    source "${PROJECT_ROOT}/.trampolinerc"
fi

log_yellow "Checking environment variables."
for e in "${required_envvars[@]}"
do
    if [[ -z "${!e:-}" ]]; then
	log "Missing ${e} env var. Aborting."
	exit 1
    fi
done

log_yellow "Preparing Docker image."
# Download the docker image specified by `TRAMPOLINE_IMAGE`

set +e  # ignore error on docker operations
# We may want to add --max-concurrent-downloads flag.

log_yellow "Start pulling the Docker image: ${TRAMPOLINE_IMAGE}."
if docker pull "${TRAMPOLINE_IMAGE}"; then
    log_green "Finished pulling the Docker image: ${TRAMPOLINE_IMAGE}."
    has_cache="true"
else
    log_red "Failed pulling the Docker image: ${TRAMPOLINE_IMAGE}."
    has_cache="false"
fi


# The default user for a Docker container has uid 0 (root). To avoid
# creating root-owned files in the build directory we tell docker to
# use the current user ID.
user_uid="$(id -u)"
user_gid="$(id -g)"
user_name="$(id -un)"

# To allow docker in docker, we add the user to the docker group in
# the host os.
docker_gid=$(cut -d: -f3 < <(getent group docker))

update_cache="false"
if [[ "${TRAMPOLINE_IMAGE_SOURCE:-none}" != "none" ]]; then
    # Build the Docker image from the source.
    context_dir=$(dirname "${TRAMPOLINE_IMAGE_SOURCE}")
    docker_build_flags=(
	"-f" "${TRAMPOLINE_IMAGE_SOURCE}"
	"-t" "${TRAMPOLINE_IMAGE}"
	"--build-arg" "UID=${user_uid}"
	"--build-arg" "GID=${user_gid}"
	"--build-arg" "USERNAME=${user_name}"
	"--build-arg" "DOCKER_GID=${docker_gid}"
    )
    if [[ "${has_cache}" == "true" ]]; then
	docker_build_flags+=("--cache-from" "${TRAMPOLINE_IMAGE}")
    fi

    log_yellow "Start building the docker image."
    if docker build "${docker_build_flags[@]}" "${context_dir}"; then
	log_green "Finished building the docker image."
	update_cache="true"
    else
	log_red "Failed to build the Docker image. Aborting."
	exit 1
    fi
else
    if [[ "${has_cache}" != "true" ]]; then
	log_red "failed to download the image ${TRAMPOLINE_IMAGE}, aborting."
	exit 1
    fi
fi

# We use an array for the flags so they are easier to document.
docker_flags=(
    # Remove the container after it exists.
    "--rm"

    # Use the host network.
    "--network=host"

    # Run in priviledged mode. We are not using docker for sandboxing or
    # isolation, just for packaging our dev tools.
    "--privileged"

    # Pass down the KOKORO_GFILE_DIR
    "--volume" "${KOKORO_GFILE_DIR:-/dev/shm}:/gfile"
    "--env" "KOKORO_GFILE_DIR=/gfile"

    # Tells scripts whether they are running as part of CI or not.
    "--env" "RUNNING_IN_CI=${RUNNING_IN_CI:-no}"

    # Run the docker script with the user id. Because the docker image gets to
    # write in ${PWD} you typically want this to be your user id.
    # Also to allow docker in docker, we use docker gid on the host.
    "--user" "${user_uid}:${docker_gid}"

    # Pass down the USER.
    "--env" "USER=${user_name}"

    # Mount the project directory inside the Docker container.
    "--volume" "${PROJECT_ROOT}:/v"
    "--workdir" "/v"
    "--env" "PROJECT_ROOT=/v"

    # Mount the temporary home directory.
    "--volume" "${tmphome}:/h"
    "--env" "HOME=/h"

    # Allow docker in docker.
    "--volume" "/var/run/docker.sock:/var/run/docker.sock"

    # Mount the /tmp so that docker in docker can mount the files
    # there correctly.
    "--volume" "/tmp:/tmp"
)

# Add an option for nicer output if the build gets a tty.
if [[ -t 0 ]]; then
    docker_flags+=("-it")
fi

# Passing down env vars
for e in "${pass_down_envvars[@]}"
do
    if [[ -n "${!e:-}" ]]; then
	docker_flags+=("--env" "${e}=${!e}")
    fi
done

# If arguments are given, all arguments will become the commands run
# in the container, otherwise run TRAMPOLINE_BUILD_FILE.
if [[ $# -ge 1 ]]; then
    log_yellow "Running the given commands '" "${@:1}" "' in the container."
    readonly commands=("${@:1}")
else
    log_yellow "Running the tests in a Docker container."
    # Temporary workaround to remove unnecessary prefix.
    real_build_file=${TRAMPOLINE_BUILD_FILE#"github/python-docs-samples/"}
    readonly commands=("/v/${real_build_file}")
fi

echo docker run "${docker_flags[@]}" "${TRAMPOLINE_IMAGE}" "${commands[@]}"
docker run "${docker_flags[@]}" "${TRAMPOLINE_IMAGE}" "${commands[@]}"

test_retval=$?

if [[ ${test_retval} -eq 0 ]]; then
    log_green "Build finished with ${test_retval}"
else
    log_red "Build finished with ${test_retval}"
fi

# Only upload it when the test passes.
if [[ "${update_cache}" == "true" ]] && \
       [[ $test_retval == 0 ]] && \
       [[ "${TRAMPOLINE_IMAGE_UPLOAD:-false}" == "true" ]]; then
    log_yellow "Uploading the Docker image."
    if docker push "${TRAMPOLINE_IMAGE}"; then
	log_green "Finished uploading the Docker image."
    else
	log_red "Failed uploading the Docker image."
    fi
fi
