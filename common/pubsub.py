from typing import Optional

from google.pubsub_v1.services.publisher.async_client import PublisherAsyncClient
from google.pubsub_v1.types import PubsubMessage


class PubSub(object):
    client = None

    class Client:
        def __init__(self, project_id: str, topic_name: str, *args, **kwargs):
            self.publisher: Optional[PublisherAsyncClient] = None
            self.project_id = project_id
            self.topic_name: str = topic_name
            self.topic_path: str = ""

        async def publisher_connected(self) -> bool:
            if self.publisher and self.topic_path:
                return True
            elif self.topic_name:
                self.publisher = PublisherAsyncClient()
                self.topic_path = self.publisher.topic_path( # type: ignore[union-attr]
                    self.project_id,
                    self.topic_name
                )
                return True

            return False

        async def publish_messages(self, message: str) -> str:
            if await self.publisher_connected():
                pub_resp = await self.publisher.publish( # type: ignore[union-attr]
                    topic=self.topic_path,
                    messages=[
                        PubsubMessage(
                            data=message.encode('utf-8')
                        ),
                    ]
                )
                for msg_id in pub_resp.message_ids:
                    return msg_id

            return ""

    def __new__(cls, project_id: str, topic_name: str, *args, **kwargs) -> Client: # type: ignore[misc]
        if cls.client is None:
            cls.client = cls.Client(
                project_id, topic_name,
                *args,
                **kwargs
            )

        return cls.client
