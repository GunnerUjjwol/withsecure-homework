import json
import base64
import os
import random
import boto3
from botocore.exceptions import EndpointConnectionError, ClientError
from botocore.config import Config
import time
from datetime import datetime

# Configuration
LOCALSTACK_ENDPOINT_URL = os.environ.get("LOCALSTACK_ENDPOINT_URL", "http://localstack:4566")

BATCH_SIZE = int(os.environ.get("BATCH_SIZE", 10))
VISIBILITY_TIMEOUT = int(os.environ.get("VISIBILITY_TIMEOUT", 30))

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

def preprocess_submission(submission):
    """
    Preprocesses a submission and extracts individual events for publishing to Kinesis.
    """
    processed_events = []
    submission_id = submission.get("submission_id")
    device_id = submission.get("device_id")
    time_processed = datetime.utcnow().isoformat()

    if not submission_id or not device_id:
        return None

    events = submission.get("events", {})
    for event_type, event_list in events.items():
        for event in event_list:
            if event_type == "new_process":
                processed_event = process_new_process_event(submission_id, device_id, time_processed, event)
            elif event_type == "network_connection":
                processed_event = process_network_connection_event(submission_id, device_id, time_processed, event)
            else:
                # Ignore unknown event types
                continue

            processed_events.append(processed_event)

    return processed_events

def process_new_process_event(submission_id, device_id, time_processed, event):
    """
    Process a 'new_process' event and return the processed event.
    """
    return {
        "event_type": "new_process",
        "submission_id": submission_id,
        "device_id": device_id,
        "time_processed": time_processed,
        "cmdl": event.get("cmdl"),
        "user": event.get("user")
    }

def process_network_connection_event(submission_id, device_id, time_processed, event):
    """
    Process a 'network_connection' event and return the processed event.
    """
    return {
        "event_type": "network_connection",
        "submission_id": submission_id,
        "device_id": device_id,
        "time_processed": time_processed,
        "source_ip": event.get("source_ip"),
        "destination_ip": event.get("destination_ip"),
        "destination_port": event.get("destination_port")
    }
    
def receive_submissions(sqs_client, queue_url):
    try:
        response = sqs_client.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=BATCH_SIZE,
        VisibilityTimeout=VISIBILITY_TIMEOUT
        )
        messages = response.get('Messages', [])
        return messages
    except (EndpointConnectionError, ClientError) as e:
        print(f"Error receiving submissions: {e}")
        return []
        

def main():
    """
    Continuously processes submissions from SQS and publishes processed events to Kinesis.
    """

    while True:
        try:
            # Receive messages from SQS
            queue_url = sqs_client.get_queue_url(QueueName='submissions')['QueueUrl']
            # print(f"trying to connect to receive message from sqs : {queue_url}")
            print("Receive submission called")
            messages = receive_submissions(sqs_client, queue_url)
            
            # print(f"Messages received: {messages}")
        
            for message in messages:
                # Process each message
                encoded_body = message['Body']
                # Decode the base64-encoded message body
                decoded_body = base64.b64decode(encoded_body)
                # Deserialize the message from JSON
                message_data = json.loads(decoded_body)
                receipt_handle = message['ReceiptHandle']

                processed_events = preprocess_submission(message_data)
                print("------------------------------------------")
                print(f"processed events : {processed_events}")

                if processed_events:
                    # Publish processed events to Kinesis stream
                    for event in processed_events:
                        kinesis_client.put_record(
                            StreamName='events',
                            Data=json.dumps(event),
                            PartitionKey=event['event_type'] #TODO: use event.event_type as partition key?
                        )

                # Delete the message from SQS
                
                sqs_client.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=receipt_handle
                )
                time.sleep(random.randint(30, 45))
        except (EndpointConnectionError, ClientError) as e:
            print(f"Error processing submissions: {e}")
            pass

if __name__ == '__main__':
    main()
