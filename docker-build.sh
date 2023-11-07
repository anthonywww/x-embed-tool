#!/bin/bash

# Change directory to the current script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR


if [[ "$(uname)" == "Darwin" ]] && [[ "$(uname -m)" == 'arm64' ]]; then
    # Mac M1+ (arm64)
    docker build --platform linux/amd64 \
        --build-arg APPLE_ARM=1 \
        -t x-embed-tool:latest .
else
    # Linux amd64
    docker build --platform linux/amd64 \
        -t x-embed-tool:latest .
fi

