import uuid
import json
from datetime import datetime

class ProcessedEvent:
    """
    Class representing a processed event.
    """
    def __init__(self, event_type, submission_id, device_id, event_data):
        self.event_id = str(uuid.uuid4())
        self.event_type = event_type
        self.submission_id = submission_id
        self.device_id = device_id
        self.time_processed = datetime.utcnow().isoformat()
        self.event_data = event_data
        
    def toJson(self):
        return json.dumps(self, default=lambda o: o.__dict__)