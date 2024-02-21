import boto3
import base64
import json
import time
import random
from botocore.config import Config
from botocore.exceptions import EndpointConnectionError, ClientError

config = Config(
    region_name = 'eu-west-1',
    retries = {
        'max_attempts': 3,
        'mode': 'standard'
    }
)

shardID = "shardId-000000000000"
# Initialize Kinesis client
kinesis_client = boto3.client('kinesis', config=config, endpoint_url="http://localstack:4566", verify=False)

def get_records(stream_name: str, shard_iterator: str):
    """
    Get records from a Kinesis data stream.

    Args:
        stream_name: Name of the Kinesis data stream.
        shard_iterator: Shard iterator obtained using get_shard_iterator().

    Returns:
        List of records.
    """
    
    try:
        response = kinesis_client.get_records(
            ShardIterator=shard_iterator,
            Limit=5  
        )
        print(f"Response: {response}")
        records = response.get('Records', [])
        return records
    except (EndpointConnectionError, ClientError) as e:
        pass

def main():
    stream_name = 'events'  
    print("Consumer Started")
    
    while True:
        # Get a shard iterator for the latest records in the stream
        shard_iterator_response = kinesis_client.get_shard_iterator(
            StreamName=stream_name,
            ShardId=shardID,
            ShardIteratorType='TRIM_HORIZON'
        )
        shard_iterator = shard_iterator_response['ShardIterator']

        # Get records using the shard iterator
        records = get_records(stream_name, shard_iterator)
        for record in records:
            # Decode the record data
            record_data = record['Data'].decode('utf-8')
            print("---------------------")
            print(f"Record Data : {record_data}")
        time.sleep(random.randint(10, 20))

if __name__ == '__main__':
    main()
