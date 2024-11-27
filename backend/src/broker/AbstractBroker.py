# pylint: disable=C0103
"""
IMPORTANT: Due to Python logic this implementation can not have an Interface to
define its behavior unless `abc.ABCMeta` is used leading to define a `cls` attribute
on all methods:

```Python
def method(cls, self, arg1):
    pass
```

Because of this, this can be considered as an abstract implementation of a generic
ContextBroker class based on the Publish-Subscribe Messaging Pattern in which publishers
send messages to a message broker, and subscribers express interest in receiving certain
messages.

The AbstractBroker module is responsible for orchestrating this information,
delivering the messages to the subscribed clients.

There are two main abstract classes with its respective functionalities:
    - Publisher
        - .subscribe()
        - .publish()
    - Subscriber
        - .receive()
"""

import queue
import time
import threading
import uuid


class AbstractBroker:
    """Near/Soft-Abstract implementation of a background Publish-Subscribe Message
    Protocol that allows to publish logs based on a unique identification relative to
    the user session driving the queries against the backend.

    - AbstractBroker `.publish()` accepts None as default identity by using
    `get_new_uuid()` to define it.
    - AbstractBroker instances have a `get_new_uuid()` method to create a
    unique ID prior to the first `.publish()`.
    - Each Platform request-session needs to keep track of its own identity either
    by creating it with `AbstractBroker.get_new_uuid()` or, by inspecting the
    `AbstractBroker.Subscriber.identity` returned by `AbstractBroker.subscribe()`.
    """

    def __init__(self, **config):
        self.message_queue = queue.Queue()
        self.subscribers = {}
        self.name = None
        for key, value in config.items():
            setattr(self, key, value)

    @staticmethod
    def get_new_uuid() -> str:
        """Returns a new str-version of UUID autogenerated key which will be unique for each
        user request to the Platform. Can be also understood as the LogsDB UID.

        Notice/TODO: In further implementations it might be necessary to address potential uuid
        being duplicated in the DB.

        Returns:
            str: Unique session ID as per each request to the platform.
        """
        return str(uuid.uuid4())

    # pylint:disable=R0903
    class Publisher:
        """Inner Publisher logic from the Publish-Subscribe Messaging Patter."""

        def __init__(self):
            self.subscribers = []

    # pylint:disable=R0903
    class Subscriber:
        """Inner Subscriber logic from the Publish-Subscribe Messaging Patter."""

        def __init__(self, identity):
            self.identity = identity
            self.event = threading.Event()
            self.message = None

        def receive(self) -> str:
            """Enters in an await statement until some new information is
            published under its topic.
            """
            self.event.wait()
            print(f"{self.identity}" + "received message:" + f"{self.message}")
            self.event.clear()
            return self.message

    def subscribe(self, identity=None) -> Subscriber:
        """Method designed to stablish a unique communication cannel under an specific
        identity in order to listen at all the messages sent thought it.

        If no identity is provided, it generates a new one using Python uuid library.

        Args:
            identity (str): Private identifier of the unique session driving the queries
            against the backend. Defaults to None.

        Returns:
            Subscriber: Subscriber object linked to the ContextBroker set of subscribers
            under a specific given identity.
        """
        if identity is None:
            identity = self.get_new_uuid()
        if identity not in self.subscribers:
            self.subscribers[identity] = []
        subscriber = self.Subscriber(identity)
        self.subscribers[identity].append(subscriber)
        return subscriber

    def unsubscribe(self, identity) -> list:
        """Antagonist method to the subscribe. This method removes an identity
        from the original set of subscribers allowing to free up space.

        Args:
            identity (str): Private identifier of the unique session driving the queries
            against the backend.

        Raises:
            ValueError: Identity provided not present in set of ContextBroker subscribers.

        Returns:
            list: List of subscribers unsubscribed relative to a specific identity.
        """
        if identity in self.subscribers:
            return self.subscribers.pop(identity)
        raise ValueError(f"Identity '{identity}' not present in set of subscribers")

    def publish(self, identity: str, topic: str, value, delay: int = 0):
        """Given an identity, the message is published against the set of subscribers
        liked to this same identity.

        Args:
            identity (str): Private identifier of the unique session driving the queries
            against the backend.
            topic (str): Context of the information to be published. e.g. "logging" to
            store information on DB
            value (any >> __str__): Information to be published. MUST be __str__ serializable!
                - For "logging" topic, it must follow a dictionary structure matching the
                ORM entity (LogModelORM) fields.
            delay (int): Amount of seconds of delay to be added to the publish operation.
                Purely DEBUG purposes.
        """
        if identity in self.subscribers:
            time.sleep(delay)
            for subscriber in self.subscribers[identity]:
                subscriber.event.set()
                subscriber.message = (topic, value)
            return None
        raise ValueError(f"Identity '{identity}' not present in set of subscribers")