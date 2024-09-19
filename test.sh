#!/bin/bash

VERSION=$(cat VERSION)

docker build . -t ghcr.io/fredoaf/traffic-alerts:$VERSION
docker push ghcr.io/fredoaf/traffic-alerts:$VERSION

API_KEY=$(cat key)

docker run --rm -it -v $PWD:/app -e API_KEY=$API_KEY \
  -e DATA_DIR='./state.json' -w /app ghcr.io/fredoaf/traffic-alerts:$VERSION