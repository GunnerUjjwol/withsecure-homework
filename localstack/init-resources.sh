#!/usr/bin/env bash
aws --endpoint-url=http://localhost:4566 sqs create-queue --queue-name submissions
aws --endpoint-url=http://localhost:4566 kinesis create-stream --stream-name events --shard-count 2
