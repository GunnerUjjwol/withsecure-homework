# Homework README

This file contains the description of the homework, the solution and explanation to the solution approach and also documents the solution specs and guides for building and running the solution.

## Homework Description

A basic element of any Endpoint Detection and Response (EDR) solution is to have an agent running on the endpoint that collects telemetry from the device. This homework requires developing a preprocessing component for an EDR backend that processes these telemetry submissions from sensors, applies some simple data reformatting to them and publishes the processed data.

## Existing Environment

Docker Compose based environment where you have the following services was provided:

- `localstack`: An open source tool which provides AWS API compatible services that can be used locally
- `sensor-fleet`: Simulating a fleet of EDR sensors which are each submitting telemetry at periodic intervals

There were 2 pre-baked resources in the Localstack environment:

- SQS queue `submissions`: incoming submissions can be read from this queue
- Kinesis stream `events`: outgoing events are published to this stream

## Solution

A new service name preprocessor-service is responsible for receiving the submissions from the queue, spread it out into individual events, and publishing the events into the Kinesis datasream. The service is bundled into a new docker image service to preserve the loosely coupled microservice architecture of the environment.
The solution is implemented in python consistent with the existing services.
The main.py continuosly runs until terminated. The solution is modularized into several modules/functions. The flow proceeds with following modules in the specified order.

1. Receive submissions - receive_submissions(sqs_client, queue_url, batch_size, visibility_timeout)

   - The submissions are polled from the SQS with configurable values for MaxNumberOfMessages and VisibilityTimeout.

2. Validate submission - validate_submission(submission_data)

   - Various validations are run against the submission data retrieved from the SQS queue. The invalidated submissions are dropped and not considered for preprocessing.

3. Preprocess submission - preprocess_submission(submission)

   - The submission data are now broken part into individual event. A uuid as an uuid and the time_processed are assigned to the outgoing event data. The submission_id, device_id and event_type attributes are also assigned to the event.
     An example of outgoing event data format is presented below:
     ```yaml
     {
       'event_type': 'new_process',
       'event_id': str(uuid.uuid4()),
       'submission_id': submission_id,
       'device_id': device_id,
       'time_processed': datetime.utcnow().isoformat(),
       'event_data': { 'cmdl': '<commandline>', 'user': '<username' }
     }
     ```

4. Publish event to Kinesis - publish_to_kinesis(events, stream_name, partition_key)

   - The individual event is puushed to the kinesis datastream "events". The submission_id is used as the partition key to distribute the events into the shards to ensure that events from each submission are orderly published to the same shard

5. Eventually, once all events from the submission is processed, the submission is deleted from the SQS queue.

## How to launch the service

The new preprocessor-service docker image specification is defined in the docker-compose.yml file.
The entire environment can be brought up with `docker-compose up -d`. This will launch three containers - localstack, sensor-fleet and the new preprocessor-service to run on the background (it may take a while to download Docker images that are used).

The preprocessor-service alone can be launched with `docker-compose up -d preprocessor-service` if other containers are already running. The image for the service can be rebuilt if needed with `docker-compose build preprocessor-service`.

To validate that the preprocessor-service have been started up properly, run the following commands to ensure event data are published to the kinesis datastream, expect similar responses as in the examples below:

Describe the stream. Obtain the shardId to be used in next command.

```console
$ docker-compose exec localstack aws --endpoint-url=http://localhost:4566 kinesis describe-stream --stream-name events
{
    "StreamDescription": {
        "Shards": [
            {
                "ShardId": "shardId-000000000000",
                "HashKeyRange": {
                    "StartingHashKey": "0",
                    "EndingHashKey": "170141183460469231731687303715884105726"
                },
                "SequenceNumberRange": {
                    "StartingSequenceNumber": "49649424801533943066477071814655986326407964284780806146"
                }
            },
            {
                "ShardId": "shardId-000000000001",
                "HashKeyRange": {
                    "StartingHashKey": "170141183460469231731687303715884105727",
                    "EndingHashKey": "340282366920938463463374607431768211455"
                },
                "SequenceNumberRange": {
                    "StartingSequenceNumber": "49649424801556243811675602437797522044680612646286786578"
                }
            }
        ],
        "StreamARN": "arn:aws:kinesis:eu-west-1:000000000000:stream/events",
        "StreamName": "events",
        "StreamStatus": "ACTIVE",
        "RetentionPeriodHours": 24,
        "EnhancedMonitoring": [
            {
                "ShardLevelMetrics": []
            }
        ],
        "EncryptionType": "NONE",
        "KeyId": null,
        "StreamCreationTimestamp": 1708371986.15
    }
}
```

Get shard iterator for a shard. An iterator is required to get records from the shard

```console
$ docker-compose exec localstack aws --endpoint-url=http://localhost:4566 kinesis get-shard-iterator --stream-name events --shard-id shardId-000000000001 --shard-iterator-type TRIM_HORIZON
{
    "ShardIterator": "AAAAAAAAAAFF7+jVVP6kv9wb+7Y7fHCf4m5QY1LkXPiXIJLyW0UkJ+V2l0R5LPYNgBmElk/XlxabvpcmpTG0tzP7ATAssmmS5Px0R920Q5UFMgNo/GBYthqEi8XQp44ja59+7amD1/K5xbzIGHs6tduVZGhItSb49HQfP4QzsTmGviGhg2rP+jEKW5fnLpP4OvagKcePXqU="
}
```

Check records published to one of the shard

```console
$ docker-compose exec localstack aws --endpoint-url=http://localhost:4566 kinesis get-records --shard-iterator AAAAAAAAAAFF7+jVVP6kv9wb+7Y7fHCf4m5QY1LkXPiXIJLyW0UkJ+V2l0R5LPYNgBmElk/XlxabvpcmpTG0tzP7ATAssmmS5Px0R920Q5UFMgNo/GBYthqEi8XQp44ja59+7amD1/K5xbzIGHs6tduVZGhItSb49HQfP4QzsTmGviGhg2rP+jEKW5fnLpP4OvagKcePXqU= --limit 3
{
    "Records": [
        {
            "SequenceNumber": "49649424801556243811675602437797522044680614432993181714",
            "ApproximateArrivalTimestamp": 1708372012.917,
            "Data": "eyJldmVudF90eXBlIjogIm5ld19wcm9jZXNzIiwgImV2ZW50X2lkIjogImU2NGY2YmNhLTI1ZmEtNGUzMC1iYWQ3LTUzODA5MTRlNDhiNCIsICJzdWJtaXNzaW9uX2lkIjogIjVjNTQ4NDJkLWJhMWEtNDZiYS04NmU4LTJjYjAzNDg1N2EyYyIsICJkZXZpY2VfaWQiOiAiNTQ2MGFlYzMtMzgyYS00ZjY3LWEyODItMmMwMzgzNWIzY2NlIiwgInRpbWVfcHJvY2Vzc2VkIjogIjIwMjQtMDItMTlUMTk6NDY6NTEuMjM3OTQ1IiwgImV2ZW50X2RhdGEiOiB7ImNtZGwiOiAiY2FsY3VsYXRvci5leGUiLCAidXNlciI6ICJhZG1pbiJ9fQ==",
            "PartitionKey": "new_process",
            "EncryptionType": "NONE"
        },
        {
            "SequenceNumber": "49649424801556243811675602437798730970500229062167887890",
            "ApproximateArrivalTimestamp": 1708372012.927,
            "Data": "eyJldmVudF90eXBlIjogIm5ld19wcm9jZXNzIiwgImV2ZW50X2lkIjogImY4MDFlOWVmLWE2ZDUtNDZiNy1iZTFiLWIwM2JhOGFmMGQ5YSIsICJzdWJtaXNzaW9uX2lkIjogIjVjNTQ4NDJkLWJhMWEtNDZiYS04NmU4LTJjYjAzNDg1N2EyYyIsICJkZXZpY2VfaWQiOiAiNTQ2MGFlYzMtMzgyYS00ZjY3LWEyODItMmMwMzgzNWIzY2NlIiwgInRpbWVfcHJvY2Vzc2VkIjogIjIwMjQtMDItMTlUMTk6NDY6NTEuMjM3OTYwIiwgImV2ZW50X2RhdGEiOiB7ImNtZGwiOiAid2hvYW1pIiwgInVzZXIiOiAiYWRtaW4ifX0=",
            "PartitionKey": "new_process",
            "EncryptionType": "NONE"
        },
        {
            "SequenceNumber": "49649424801556243811675602437799939896319843691342594066",
            "ApproximateArrivalTimestamp": 1708372012.939,
            "Data": "eyJldmVudF90eXBlIjogIm5ld19wcm9jZXNzIiwgImV2ZW50X2lkIjogImUyMWJjZjU0LTExODktNDQyNS1iNzVkLTI1MTdhM2JmYWU5ZCIsICJzdWJtaXNzaW9uX2lkIjogIjVjNTQ4NDJkLWJhMWEtNDZiYS04NmU4LTJjYjAzNDg1N2EyYyIsICJkZXZpY2VfaWQiOiAiNTQ2MGFlYzMtMzgyYS00ZjY3LWEyODItMmMwMzgzNWIzY2NlIiwgInRpbWVfcHJvY2Vzc2VkIjogIjIwMjQtMDItMTlUMTk6NDY6NTEuMjM3OTY4IiwgImV2ZW50X2RhdGEiOiB7ImNtZGwiOiAibm90ZXBhZC5leGUiLCAidXNlciI6ICJhZG1pbiJ9fQ==",
            "PartitionKey": "new_process",
            "EncryptionType": "NONE"
        }
    ],
    "NextShardIterator": "AAAAAAAAAAFRp9nPi67gF/9mhsjwfp7VK8kiX9E2DAkLAPUwzeMNkN48WMGjbRxeU6RBcf7hqCra4Jg197wpeaDaXGGJkjMaXnnJ2ksbTGcOauEVKbTLPIAl7CcFWe3LXSt6NPSvBHd9AImQRM14rf8JSsLW1l6S1j4ipalxWYTG1rkpw3zCkbliORNX6L6ukdHFbH2To=",
    "MillisBehindLatest": 532776,
    "ChildShards": []
}
```

The records from next shard can be similarly checked with the shardIterator for another shard.

### Requirements Fulfillment notes

- each event is published as an individual record to kinesis (one submission is turned into multiple events)
  - Fulfillment note - the preprocess_submission(submission) function parses the submission json into individual event. Each event is individually passed on to the kinesis stream.
- each event must have information of the event type (`new_process` or `network_connection`)
  - Fulfillment note - event_type attribute in the event dict specify the event type
- each event must have an unique identifier
  - Fulfillment note - An UUID is created by leveraging the uuid library.
- each event must have an identifier of the source device (`device_id`)
- each event must have a timestamp when it was processed (backend side time in UTC)
- submissions are validated and invalid or broken submissions are dropped #TODO
  - Fulfillment note - validate_submission(submission_data) looks after the validation of the submission.
- must guarantee no data loss (for valid data), i.e. submissions must not be deleted before all events are succesfully published #TODO
- must guarantee ordering of events in the context of a single submission #TODO
  - Fulfillment note - To ensure ordering of events in the context of a single submission, "submission_id" is used as the PartitionKey while putting events to the Kinesis Stream. This will ensure that all the events belonging to the same submission are sent to the same shard in the Kinesis stream, preserving their order of arrival.
- the number of messages read from SQS with a single request must be configurable
- the visibility timeout of read SQS messages must be configurable
  - Fulfillment note - The MaxNumberOfMessages and the VisibilityTimeout configs for the SQS queue message retrieval are made configurable as environment variables in the Dockerfile with the fallback default values specified in the code. The value of those will be configurable during the docker image build time.

### Deliverables

- All used source code is freely distributable.
