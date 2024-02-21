import unittest
from processed_event import ProcessedEvent


class TestValidateEvent(unittest.TestCase):

    def test_validate_event_new_process_valid(self):
        event_data = {"cmdl": "notepad.exe", "user": "admin"}
        event = ProcessedEvent(
            "new_process",
            "b31a90ea-5fb2-4162-b7ba-0f50cf7ad687",
            "b31a90ea-5fb2-4162-b7ba-0f50cf7ad687",
            event_data,
        )
        self.assertTrue(event.validate_event())

    def test_validate_event_new_process_invalid(self):
        # Missing 'user' key in event data
        event_data = {"cmdl": "notepad.exe"}
        event = ProcessedEvent(
            "new_process",
            "b31a90ea-5fb2-4162-b7ba-0f50cf7ad687",
            "b31a90ea-5fb2-4162-b7ba-0f50cf7ad687",
            event_data,
        )
        self.assertFalse(event.validate_event())

    def test_validate_event_network_connection_valid(self):
        event_data = {
            "source_ip": "192.168.1.1",
            "destination_ip": "10.0.0.1",
            "destination_port": 8080,
        }
        event = ProcessedEvent(
            "network_connection", "submission_id", "device_id", event_data
        )
        self.assertTrue(event.validate_event())

    def test_validate_event_network_connection_invalid(self):
        # Invalid destination port
        event_data = {
            "source_ip": "192.168.1.1",
            "destination_ip": "10.0.0.1",
            "destination_port": "invalid",
        }
        event = ProcessedEvent(
            "network_connection",
            "b31a90ea-5fb2-4162-b7ba-0f50cf7ad687",
            "b31a90ea-5fb2-4162-b7ba-0f50cf7ad687",
            event_data,
        )
        self.assertFalse(event.validate_event())


if __name__ == "__main__":
    unittest.main()
