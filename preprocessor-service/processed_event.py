import uuid
import json
from datetime import datetime


class ProcessedEvent:

    NEW_PROCESS_EVENT = "new_process"
    NETWORK_CONNECTION_EVENT = "network_connection"
    """
    Class representing a processed event.
    """

    def __init__(
        self, event_type: str, submission_id: str, device_id: str, event_data: dict
    ):
        self.event_id = str(uuid.uuid4())
        self.event_type = event_type
        self.submission_id = submission_id
        self.device_id = device_id
        self.time_processed = datetime.utcnow().isoformat()
        self.event_data = event_data

    def toJson(self):
        return json.dumps(self, default=lambda o: o.__dict__)

    def validate_event(self):
        # Checks for event_type : new_process
        if self.event_type == self.NEW_PROCESS_EVENT:
            if not all(key in self.event_data for key in ["cmdl", "user"]):
                print(
                    f"Detected invalid event key apart from 'cmdl' and 'user'. Dropping event :{self.event_data}"
                )
                return False
            if not isinstance(self.event_data["cmdl"], str) or not isinstance(
                self.event_data["user"], str
            ):
                print(
                    f"Detected invalid Cmdl or user. Dropping event :{self.event_data}"
                )
                return False
        # Checks for event_type : network_connection
        elif self.event_type == self.NETWORK_CONNECTION_EVENT:
            if not all(
                key in self.event_data
                for key in ["source_ip", "destination_ip", "destination_port"]
            ):
                print(
                    f"Detected invalid event key apart from 'source_ip', 'destination_ip' and 'destination_port' in event:{self.event_data}"
                )
                return False
            if not isinstance(self.event_data["source_ip"], str) or not isinstance(
                self.event_data["destination_ip"], str
            ):
                print(
                    f"Detected invalid source_ip or destination_ip. Dropping event :{self.event_data}"
                )
                return False
            if not isinstance(self.event_data["destination_port"], int):
                print(
                    f"Detected invalid destination_port. Dropping event :{self.event_data}"
                )
                return False
        return True
