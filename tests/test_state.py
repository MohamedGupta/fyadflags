from unittest import mock, TestCase
from json_state import state


class TestJsonState(TestCase):
    @mock.patch("json_state.state.LOCALSTATE")
    def test_save_load_state(self, mock_localstate_path):
        mock_localstate_path.return_value = "test_state.json"
        state_dict = {"state": "value"}
        state.save(state_dict)
        self.assertEqual(state_dict, state.load())
