import unittest
import tweeter

class TwitterAction(unittest.TestCase):
    def test_twitter_oauth(self):
        """Test Twitter OAuth authentication."""
        # Initialize the Twitter client with test credentials
        client = tweeter.TwitterClient(
            consumer_key='test_consumer_key',
            consumer_secret='test_consumer_secret',
            access_token='test_access_token',
            access_token_secret='test_access_token_secret'
        )

        # Attempt to authenticate
        try:
            client.authenticate()
            self.assertTrue(client.is_authenticated, "Twitter authentication failed")
        except Exception as e:
            self.fail(f"Twitter authentication raised an exception: {e}")


if __name__ == '__main__':
    unittest.main()
