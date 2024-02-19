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

# Configuration
LOCALSTACK_ENDPOINT_URL = os.environ.get("LOCALSTACK_ENDPOINT_URL", "http://localstack:4566")

BATCH_SIZE = int(os.environ.get("BATCH_SIZE", 10))
VISIBILITY_TIMEOUT = int(os.environ.get("VISIBILITY_TIMEOUT", 30))

STREAM_NAME = "events"

config = Config(
    region_name = 'eu-west-1',
    retries = {
        'max_attempts': 3,
        'mode': 'standard'
    }
)

# AWS Clients
sqs_client = boto3.client('sqs', config=config, endpoint_url=LOCALSTACK_ENDPOINT_URL, verify=False)
kinesis_client = boto3.client('kinesis', config=config, endpoint_url=LOCALSTACK_ENDPOINT_URL, verify=False)

def receive_submissions(sqs_client, queue_url, batch_size, visibility_timeout):
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
        VisibilityTimeout=visibility_timeout
        )
        messages = response.get('Messages', [])
        return messages
    except (EndpointConnectionError, ClientError) as e:
        #TODO: return or pass?
        # print(f"Error receiving submissions: {e}")
        # return []
        pass

def validate_submission(submission_data):
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
        return False

    # Check data types of required fields
    if not isinstance(submission_data["submission_id"], str) or not is_valid_uuid(submission_data["submission_id"]):
        return False
    if not isinstance(submission_data["device_id"], str) or not is_valid_uuid(submission_data["device_id"]):
        return False
    if not isinstance(submission_data["time_created"], str):
        return False
    if not isinstance(submission_data["events"], dict):
        return False

    # Check if 'events' field contains valid data
    events = submission_data["events"]
    for event_type, event_list in events.items():
        if not isinstance(event_list, list):
            return False
        for event in event_list:
            if event_type == "new_process":
                if not all(key in event for key in ["cmdl", "user"]):
                    return False
                if not isinstance(event["cmdl"], str) or not isinstance(event["user"], str):
                    return False
            elif event_type == "network_connection":
                if not all(key in event for key in ["source_ip", "destination_ip", "destination_port"]):
                    return False
                if not isinstance(event["source_ip"], str) or not isinstance(event["destination_ip"], str):
                    return False
                if not isinstance(event["destination_port"], int):
                    return False
            else:
                return False  # Unknown event type

    return True

def is_valid_uuid(uuid_str):
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

def preprocess_submission(submission):
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
            processed_event = {
                "event_type": "new_process | network_connection",
                "event_id": str(uuid.uuid4()),
                "submission_id": submission_id,
                "device_id": device_id,
                "time_processed": datetime.utcnow().isoformat(),
                "event_data": event
            }
            if event_type == "new_process":
                # processed_event = process_new_process_event(submission_id, device_id, event)
                processed_event['event_type']: "new-process"
            elif event_type == "network_connection":
                # processed_event = process_network_connection_event(submission_id, device_id, event)
                processed_event['event_type']: "network_connection"
            else:
                # Ignore unknown event types
                continue
            

            processed_events.append(processed_event)

    return processed_events


def publish_to_kinesis(events, stream_name, partition_key):
    """
    Publish individual event to kinesis data stream 

    Args:
        events         : Events
        stream_name       : Kinesis stream
        partition_key : PartitionKey for kinesis shards distribution
    """
    try:
        for event in events:
                kinesis_client.put_record(
                    StreamName=stream_name,
                    Data=json.dumps(event),
                    PartitionKey=partition_key #TODO: use event.event_type as partition key?
                )
        
    except (EndpointConnectionError, ClientError) as e:
        pass
        # return   

        

def main():
    """
    Continuously processes submissions from SQS and publishes processed events to Kinesis.
    """

    # print(f"BATCH_SIZE: {BATCH_SIZE} VISIBILITY_TIMEOUT: {VISIBILITY_TIMEOUT}")
    while True:
        try:
            # Receive messages from SQS
            queue_url = sqs_client.get_queue_url(QueueName='submissions')['QueueUrl']
            # print(f"trying to connect to receive message from sqs : {queue_url}")
            print("Receive submission called")
            messages = receive_submissions(sqs_client, queue_url, BATCH_SIZE, VISIBILITY_TIMEOUT)
        
            for message in messages:
                # Process each message
                encoded_body = message['Body']
                # Decode the base64-encoded message body
                decoded_body = base64.b64decode(encoded_body)
                # Deserialize the message from JSON
                message_data = json.loads(decoded_body)
                receipt_handle = message['ReceiptHandle']
                
                #TODO: Add validations, for all fields
                if not validate_submission(submission):
                    print(f"Dropped invalid submission data: {submission}")
                    return None

                processed_events = preprocess_submission(message_data)

                # print(f"processed events : {processed_events}")

                if processed_events:
                    # Publish processed events to Kinesis stream
                    for event in processed_events:
                        publish_to_kinesis(processed_events,STREAM_NAME, event['submission_id'])
                        # print("------------------------------------------")
                        # print(f"{datetime.utcnow().isoformat()}")
                        # print(f"Pushing Event to Kinesis: {event}")
                        # kinesis_client.put_record(
                        #     StreamName='events',
                        #     Data=json.dumps(event),
                        #     PartitionKey=event['submission_id'] #TODO: use event.event_type as partition key?
                        # )

                # Delete the message from SQS
                
                sqs_client.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=receipt_handle
                )
                #TODO: Do something about this, remove??
                time.sleep(random.randint(30, 45))
        except (EndpointConnectionError, ClientError) as e:
            print(f"Error processing submissions: {e}")
            pass

if __name__ == '__main__':
    main()
