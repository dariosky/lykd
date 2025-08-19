import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

import settings

logger = logging.getLogger(__name__)


class SlackBot:
    """Slack bot service for sending messages to channels"""

    def __init__(self, channel: str = "#lykd"):
        self.token = settings.SLACK_TOKEN
        self.channel = channel
        if self.token:
            self.client = WebClient(token=self.token)
        else:
            self.client = None

    def send_message(self, text: str, channel: str | None = None) -> bool:
        target_channel = channel or self.channel
        if not self.client:
            logger.info(text)
            return False

        try:
            response = self.client.chat_postMessage(channel=target_channel, text=text)

            if response["ok"]:
                return True
            else:
                logger.error(
                    f"Failed to send message: {response.get('error', 'Unknown error')}"
                )
                return False

        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Slack message: {str(e)}")
            return False


# Convenience functions for easy usage
slack = SlackBot()
