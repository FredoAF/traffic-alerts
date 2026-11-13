#!/bin/bash
# Local smoke test only. Publishing is done by GitHub Actions (.github/workflows/docker-build.yml).
# Expects Redis on localhost, e.g. kubectl -n redis port-forward svc/redis-service 6379

set -e
API_KEY=$(cat key)

docker build . -t traffic-alerts:dev

docker run --rm -it --network host -e API_KEY=$API_KEY -e REDIS_HOST=localhost \
  --entrypoint /bin/ash traffic-alerts:dev
