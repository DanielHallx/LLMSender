import os
from dotenv import load_dotenv
import unittest
import tweepy

class TwitterAction(unittest.TestCase):
    def test_twitter_oauth(self):
        """Test Twitter OAuth authentication."""
        # Load .env configuration
        load_dotenv()

        consumer_key = str(os.environ.get('TWITTER_CONSUMER_KEY'))
        consumer_secret = str(os.environ.get('TWITTER_CONSUMER_SECRET'))
        access_token = str(os.environ.get('TWITTER_ACCESS_TOKEN'))
        access_token_secret = str(os.environ.get('TWITTER_ACCESS_TOKEN_SECRET'))
        # Initialize the Twitter client with credentials from environment variables
        client = tweepy.Client(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
            wait_on_rate_limit=True
        )

        # Test authentication by making a simple API call
        try:
            me = client.get_me()
            print(f"Authenticated as: {me.data.name} (@{me.data.username})")
            self.assertIsNotNone(me.data, "Failed to authenticate - could not retrieve user info")
            self.assertIsInstance(me.data.id, (str, int), "User ID should be a string or integer")
        except Exception as e:
            self.fail(f"Twitter authentication failed with exception: {e}")


if __name__ == '__main__':
    unittest.main()
