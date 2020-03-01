from unittest import TestCase

from main import post_flag_from_dm, refresh_follows


class DMTest(TestCase):
    def test_get_dm_with_media(self):
        #refresh_follows()
        post_flag_from_dm()