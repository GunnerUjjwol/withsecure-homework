import unittest
from main import validate_submission


class TestValidateSubmission(unittest.TestCase):

    def test_valid_submission(self):
        submission_data = {
            "submission_id": "123e4567-e89b-12d3-a456-426614174000",
            "device_id": "123e4567-e89b-12d3-a456-426614174001",
            "time_created": "2022-02-18T10:00:00Z",
            "events": {
                "new_process": [{"cmdl": "whoami", "user": "john"}],
                "network_connection": [
                    {
                        "source_ip": "192.168.1.1",
                        "destination_ip": "192.168.1.2",
                        "destination_port": 80,
                    }
                ],
            },
        }
        self.assertTrue(validate_submission(submission_data))

    def test_missing_required_fields(self):
        # missing submission_id
        submission_data = {
            "device_id": "123e4567-e89b-12d3-a456-426614174001",
            "time_created": "2022-02-18T10:00:00Z",
            "events": {
                "new_process": [{"cmdl": "whoami", "user": "john"}],
                "network_connection": [
                    {
                        "source_ip": "192.168.1.1",
                        "destination_ip": "192.168.1.2",
                        "destination_port": 80,
                    }
                ],
            },
        }
        self.assertFalse(validate_submission(submission_data))

    def test_invalid_submission_id(self):
        submission_data = {
            "submission_id": "invalid_id",
            "device_id": "123e4567-e89b-12d3-a456-426614174001",
            "time_created": "2022-02-18T10:00:00Z",
            "events": {
                "new_process": [{"cmdl": "whoami", "user": "john"}],
                "network_connection": [
                    {
                        "source_ip": "192.168.1.1",
                        "destination_ip": "192.168.1.2",
                        "destination_port": 80,
                    }
                ],
            },
        }
        self.assertFalse(validate_submission(submission_data))

    def test_missing_event_type(self):
        submission_data = {
            "submission_id": "123e4567-e89b-12d3-a456-426614174000",
            "device_id": "123e4567-e89b-12d3-a456-426614174001",
            "time_created": "2022-02-18T10:00:00Z",
            "events": {"invalid_type": [{"cmdl": "whoami", "user": "john"}]},
        }
        self.assertFalse(validate_submission(submission_data))


if __name__ == "__main__":
    unittest.main()
