import unittest

from main import validate_submission

class TestValidateSubmission(unittest.TestCase):
    def test_valid_submission(self):
        submission_data = {
            'submission_id': '123e4567-e89b-12d3-a456-426614174000',
            'device_id': '7890abcd-12ef-34gh-ijkl-5678mnopqrst',
            'time_created': '2024-02-18T18:45:11.468496',
            'events': {
                'new_process': [
                    {'cmdl': 'command1', 'user': 'user1'},
                    {'cmdl': 'command2', 'user': 'user2'}
                ],
                'network_connection': [
                    {'source_ip': '192.168.0.1', 'destination_ip': '192.168.0.2', 'destination_port': 12345},
                    {'source_ip': '192.168.0.2', 'destination_ip': '192.168.0.3', 'destination_port': 54321}
                ]
            }
        }
        self.assertTrue(validate_submission(submission_data))

    def test_missing_fields(self):
        submission_data = {
            'device_id': '7890abcd-12ef-34gh-ijkl-5678mnopqrst',
            'time_created': '2024-02-18T18:45:11.468496',
            'events': {
                'new_process': [
                    {'cmdl': 'command1', 'user': 'user1'}
                ]
            }
        }
        self.assertFalse(validate_submission(submission_data))

    def test_invalid_uuids(self):
        submission_data = {
            'submission_id': 'invalid_uuid',
            'device_id': '7890abcd-12ef-34gh-ijkl-5678mnopqrst',
            'time_created': '2024-02-18T18:45:11.468496',
            'events': {
                'new_process': [
                    {'cmdl': 'command1', 'user': 'user1'}
                ]
            }
        }
        self.assertFalse(validate_submission(submission_data))

    def test_invalid_event_data(self):
        submission_data = {
            'submission_id': '123e4567-e89b-12d3-a456-426614174000',
            'device_id': '7890abcd-12ef-34gh-ijkl-5678mnopqrst',
            'time_created': '2024-02-18T18:45:11.468496',
            'events': {
                'new_process': [
                    {'cmdl': 'command1'}
                ]
            }
        }
        self.assertFalse(validate_submission(submission_data))

if __name__ == '__main__':
    unittest.main()
