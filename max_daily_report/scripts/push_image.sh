#!/bin/sh
# Build the application image with an immutable commit-SHA tag, tag as latest,
# and push both to Yandex Container Registry (YC03).
#
# Usage:
#   export YCR_REGISTRY=cr.yandex/<registry-id>
#   ./scripts/push_image.sh
#
# Requires: docker login to YCR performed beforehand (yc container registry
# credentials or OAuth token). Prints the pushed image digest for rollback.
set -e

cd "$(dirname "$0")/.."

if [ -z "${YCR_REGISTRY:-}" ]; then
    echo "ERROR: YCR_REGISTRY is not set (e.g. cr.yandex/abcd1234)" >&2
    exit 1
fi

TAG="$(git rev-parse --short HEAD)"
LOCAL="max_daily_report-api"
REMOTE="${YCR_REGISTRY}/mdr-api"

echo "Building production image (tag ${TAG})..."
docker compose -f docker-compose.prod.yml build api

echo "Tagging ${LOCAL} -> ${REMOTE}:${TAG} and ${REMOTE}:latest"
docker tag "${LOCAL}" "${REMOTE}:${TAG}"
docker tag "${LOCAL}" "${REMOTE}:latest"

echo "Pushing ${REMOTE}:${TAG}"
docker push "${REMOTE}:${TAG}"
echo "Pushing ${REMOTE}:latest"
docker push "${REMOTE}:latest"

DIGEST="$(docker inspect --format='{{index .RepoDigests 0}}' "${REMOTE}:${TAG}")"
echo ""
echo "Pushed: ${REMOTE}:${TAG}"
echo "Digest: ${DIGEST}"
echo "Rollback: docker pull ${REMOTE}:<previous-tag>"
