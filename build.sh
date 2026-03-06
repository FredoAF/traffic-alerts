#!/bin/bash

VERSION=$(cat VERSION)

docker build . -t ghcr.io/fredoaf/traffic-alerts:$VERSION
docker push ghcr.io/fredoaf/traffic-alerts:$VERSION

API_KEY=$(cat key)

docker run --rm -it -e API_KEY=$API_KEY --entrypoint /bin/ash\
  -e DATA_DIR='./' -w /app ghcr.io/fredoaf/traffic-alerts:$VERSION