import json
import base64
import os
import random
import uuid
import boto3
from botocore.exceptions import EndpointConnectionError, ClientError
from botocore.config import Config
import time
from datetime import datetime
from processed_event import ProcessedEvent

# Configuration
AWS_ENDPOINT_URL = os.environ.get("AWS_ENDPOINT_URL", "http://localstack:4566")

BATCH_SIZE = int(os.environ.get("BATCH_SIZE", 5))
VISIBILITY_TIMEOUT = int(os.environ.get("VISIBILITY_TIMEOUT", 15))

STREAM_NAME = "events"

NEW_PROCESS_EVENT = "new_process"
NETWORK_CONNECTION_EVENT = "network_connection"

EVENT_TYPES = {NEW_PROCESS_EVENT, NETWORK_CONNECTION_EVENT}

config = Config(
    region_name="eu-west-1", retries={"max_attempts": 3, "mode": "standard"}
)


def receive_submissions(
    sqs_client, queue_url: str, batch_size: int, visibility_timeout: int
):
    """
    Receive messages from SQS

    Args:
        sqs_client          : The handle for SQS client
        queue_url           : The URL of the Queue
        batch_size          : Configurable MaxNumberOfMessages polled from the queue at a time
        visibility_timeout  : Configurable Visibility timeout to lock the message for other consumers.

    Returns:
        List of messages from queue
    """
    try:
        response = sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=batch_size,
            VisibilityTimeout=visibility_timeout,
        )
        messages = response.get("Messages", [])
        return messages
    except (EndpointConnectionError, ClientError) as e:
        pass


def validate_submission(submission_data: dict):
    """
    Validates the submission data.

    Args:
    submission_data: Decoded submission data

    Returns:
    True if the submission is valid, False otherwise.
    """
    required_fields = ["submission_id", "device_id", "time_created", "events"]

    # Check if all required fields are present
    if not all(field in submission_data for field in required_fields):
        print("Missing required fields")
        print(f"Dropping submission: {submission_data}")
        return False

    # Check data types of required fields
    if not isinstance(submission_data["submission_id"], str) or not is_valid_uuid(
        submission_data["submission_id"]
    ):
        print("Detected invalid submission id")
        print(f"Dropping submission: {submission_data}")
        return False
    if not isinstance(submission_data["device_id"], str) or not is_valid_uuid(
        submission_data["device_id"]
    ):
        print("Detected invalid device id ")
        print(f"Dropping submission: {submission_data}")
        return False
    if not isinstance(submission_data["time_created"], str):
        print("Detected invalid time created")
        print(f"Dropping submission: {submission_data}")
        return False
    if not isinstance(submission_data["events"], dict):
        print("events not dict type: not valid")
        print(f"Dropping submission: {submission_data}")
        return False

    # Check if 'events' field contains valid data
    events = submission_data["events"]
    for event_type, event_list in events.items():
        # Check if event_type is one of the accepted types
        if event_type not in EVENT_TYPES:
            print(f"Detected invalid event_type : {event_type}")
            print(f"Dropping submission: {submission_data}")
            return False
        # Check if event for each event_type is in list format in submissions
        if not isinstance(event_list, list):
            print(f"Event_value not formatted as list in submission")
            print(f"Dropping submission: {submission_data}")
            return False

    return True


def is_valid_uuid(uuid_str: str):
    """
    Validation function for uuid

    Args:
        uuid_str : uuid

    Returns:
        True if valid, False otherwise
    """
    try:
        uuid_obj = uuid.UUID(uuid_str)
    except ValueError:
        return False
    return str(uuid_obj) == uuid_str


def preprocess_submission(submission: dict):
    """
    Preprocesses a submission and
    extracts individual events for publishing to Kinesis.

    Args:
        submission : The message data from the queue to be prrocesses

    Returns:
        List of individual processed events
    """
    processed_events = []
    submission_id = submission.get("submission_id")
    device_id = submission.get("device_id")

    events = submission.get("events", {})
    for event_type, event_list in events.items():
        for event in event_list:
            processed_event = ProcessedEvent(
                event_type, submission_id, device_id, event_data=event
            )
            processed_events.append(processed_event)

    return processed_events


def publish_to_kinesis(kinesis_client, events: dict):
    """
    Publish individual event to kinesis data stream

    Args:
        events         : Events
    """
    try:
        for event in events:
            kinesis_client.put_record(
                StreamName=STREAM_NAME,
                Data=json.dumps(event),
                PartitionKey=event["submission_id"],
            )

    except (EndpointConnectionError, ClientError) as e:
        pass


def delete_from_queue(sqs_client, queue_url: str, receipt_handle):
    """
    Delete message from Queue

    Args:
        sqs_client      : The handle for SQS client
        queue_url       : The URL of the Queue
        receipt_handle  : Unique identifier associated with a message from SQS
    """
    try:
        sqs_client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
    except (EndpointConnectionError, ClientError) as e:
        pass


def main():
    """
    Continuously processes submissions from SQS and publishes processed events to Kinesis.
    """
    print("Starting preprocessor service")

    # initialize AWS Clients
    sqs_client = boto3.client(
        "sqs", config=config, endpoint_url=AWS_ENDPOINT_URL, verify=False
    )
    kinesis_client = boto3.client(
        "kinesis", config=config, endpoint_url=AWS_ENDPOINT_URL, verify=False
    )

    while True:
        try:
            queue_url = sqs_client.get_queue_url(QueueName="submissions")["QueueUrl"]
            # Receive messages from SQS
            messages = receive_submissions(
                sqs_client, queue_url, BATCH_SIZE, VISIBILITY_TIMEOUT
            )

            for message in messages:
                # Process each message
                encoded_body = message["Body"]
                # Decode the base64-encoded message body
                decoded_body = base64.b64decode(encoded_body)
                # Deserialize the message from JSON
                message_data = json.loads(decoded_body)
                receipt_handle = message["ReceiptHandle"]

                # validate submission
                if not validate_submission(message_data):
                    # Improvement Idea: Alternatively move the invalid submission to dead letter queues
                    delete_from_queue(sqs_client, queue_url, receipt_handle)
                    print(f"Dropped invalid submission data from queue: {message_data}")
                    continue

                processed_events = preprocess_submission(submission=message_data)

                if processed_events:
                    # validate each processed event
                    valid_events = [
                        json.loads(event.toJson())
                        for event in processed_events
                        if event.validate_event()
                    ]

                    # Publish processed events to Kinesis stream
                    print("------------------------------------------")
                    print(
                        f"{datetime.utcnow().isoformat()} Publishing Events to Kinesis: {valid_events}"
                    )
                    # publish_to_kinesis(kinesis_client, processed_events)
                    publish_to_kinesis(kinesis_client, valid_events)

                # Delete the message from SQS
                delete_from_queue(sqs_client, queue_url, receipt_handle)

                time.sleep(random.randint(5, 15))
        except (EndpointConnectionError, ClientError) as e:
            pass


if __name__ == "__main__":
    main()
