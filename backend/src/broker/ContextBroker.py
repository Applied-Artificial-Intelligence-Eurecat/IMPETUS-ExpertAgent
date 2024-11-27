# pylint: disable=C0103
"""
Vanilla-Platform Broker designed to run as a background service to log information
in a simple local DataBase.
"""

import copy
import time

from datetime import datetime
from threading import Event, Lock, Thread

from sqlalchemy.orm.exc import NoResultFound

from src.broker.AbstractBroker import AbstractBroker
from src.logger.SqliteLogger import SqliteLogger
from src.logger.database import LogModelORM


class ContextBrokerSingletonMeta(type):
    """
    This is a thread-safe implementation of Singleton.
    """

    _instances = {}
    # Lock object will be used to synchronize threads during first access to the Singleton.
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
        """
        Possible changes to the value of the `__init__` argument do not affect
        the returned instance.

        Now, imagine that the program has just been launched. Since there's no
        Singleton instance yet, multiple threads can simultaneously pass the
        previous conditional and reach this point almost at the same time. The
        first of them will acquire lock and will proceed further, while the
        rest will wait here.

        The first thread to acquire the lock, reaches this conditional,
        goes inside and creates the Singleton instance. Once it leaves the
        lock block, a thread that might have been waiting for the lock
        release may then enter this section. But since the Singleton field
        is already initialized, the thread won't create a new object.

        Raises:
            ValueError: Invalid parameters provided.

        Returns:
            ContextBrokerSingletonMeta: Singleton-safe instance.
        """
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]


class ContextBroker(AbstractBroker, metaclass=ContextBrokerSingletonMeta):
    """Vanilla implementation of a background Publish-Subscribe Message Protocol
    that allows to publish logs based on a unique identification relative to the
    user session driving the queries against the backend.

    This Abstract Class implementation implements as well the Singleton design patter.
    As a result, all the calls to this same class will return a unique instance. This
    allows to have a single background orchestrator for the entire platform.

    Args:
        AbstractBroker (backend.src.broker.AbstractBroker): Interface class designed
        to build custom Publisher classes out of the same template.
    """

    __db_name = None

    def __init__(self, max_subscribers=5, **config):
        """Creation of ContextBroker.

        Args:
            max_subscribers (int, optional): max amount of subscribers per session
            (identity). Defaults to 5.
        """
        super().__init__(**config)
        self.max_subscribers = max_subscribers

    # pylint:disable=R0903, R0902
    class Subscriber(Thread):
        """
        Inner Subscriber logic from the Publish-Subscribe Messaging Patter.

        Attributes:
        - history: Temporary history of last N messages sent though the pipe.
        - history_len: Max N-length of the `history` attribute.
        - identity: Each new Subscriber attached to a Topic needs to provide
        an identity to be able to differentiate them. This will later help
        on integration by allowing asynchronous fill of DB log rows.
        - msg_event: Becomes the main trigger of a Subscriber and it only
        gets shout out once a message is published on the pipe.
        - message: Information which triggered the published-on-pipe
        `msg_event`.
        - is_permanent_hear: Whenever the background Thread for logging
        purposes wants to be run (True) or not (False). Running in False mode
        MUST use the receive() method instead of the permanent_hear() one.
        Defaults to False.
        - _stop_event: becomes the close() trigger to the Subscriber. Used to
        finish its task and release it from the list of hearing points.
        """

        def __init__(self, identity, history_len=5):
            self._db_name = None
            super().__init__()
            self.history = []
            self.history_len = history_len
            self.identity = identity
            self.msg_event = Event()
            self.message = (None, None)
            self.is_permanent_hear = False
            self._stop_event = Event()

        def stop(self):
            """Terminates the Subscriber execution"""
            self.message = None  # Sets no message (Close ACK)
            self._stop_event.set()  # Sets while-break condition
            self.msg_event.set()  # Breaks the blocking statement to do 1 while loop

        def run(self):
            self.permanent_hear()

        def get_history(self):
            """Obtains the current up-to-date history of a specific Subscriber identity."""
            return self.history

        def permanent_hear(self):
            """Continuous-time receive. Thread-intended function to be launched along
            with a subscribe(..., permanent_hear=True) creation."""
            # TODO Why publish is not triggering a while loop?
            while not self._stop_event.is_set():
                self.msg_event.wait()
                if len(self.history) >= self.history_len:
                    self.history.pop(0)
                if self.message is not None:
                    received_message = self.message
                    topic, content = received_message[0], received_message[1]
                    self.__handle_publish(topic=topic, content=content)
                    self.history.append([str(datetime.now()), received_message])
                self.msg_event.clear()

        def receive(self) -> str:
            """One-time receive. Enters in a BLOCKING await statement until some new
            information is published under its topic.
            """
            self.msg_event.wait()
            received_message = self.message
            topic, content = received_message[0], received_message[1]

            self.__handle_publish(topic=topic, content=content)

            self.msg_event.clear()
            return received_message

        def set_db_name(self, db_name: str):
            """Forces to configure the DB reference in which the Subscriber
            will point into.

            Args:
                db_name (str): Reference name to the database in the local
                space of the databases.
            """
            self._db_name = db_name

        def __handle_publish(self, topic: str, content) -> None:
            if topic == "logging":  # Logging topic
                self.__handle_logging(content)

        def __handle_logging(self, content):
            """
            Logic relative to the Logging topic of the ContextBroker
            """
            al = SqliteLogger(db_name=self._db_name)
            base_entity = LogModelORM(id=self.identity)

            # Subtract complex logic (Nested classes)
            documents = content.pop("documents", [])

            for attr, value in content.items():
                if hasattr(base_entity, attr):
                    setattr(base_entity, attr, value)

            try:
                al.update_log_by_id(self.identity, **content)
            except NoResultFound:
                al.insert_log(base_entity)

            # Docs nested logic
            for doc in documents:
                if "id" in doc and al.is_doc_id_in_log_documents(
                    self.identity, doc["id"]
                ):
                    al.update_document_by_log_id_and_doc_id(
                        self.identity, doc["id"], doc
                    )
                else:
                    al.insert_document_by_log_id(self.identity, doc)

    def subscribe(self, identity=None, permanent_hear=True) -> Subscriber:
        """Method designed to stablish a unique communication cannel under an specific
        identity in order to listen at all the messages sent thought it.

        Args:
            identity (str): Private identifier of the unique session driving the queries
            against the backend.
            permanent_hear (bool, optional): Whenever the background Thread for logging
            purposes wants to be run (True) or not (False). Running in False mode MUST use
            the receive() method instead of the permanent_hear() one.

        Raises:
            ValueError: When the user tries to set more than `max_subscribers` Subscriber
            connections for a unique identity.

        Returns:
            Subscriber: Subscriber object linked to the ContextBroker set of subscribers
            under a specific given identity.
        """
        if identity is None:
            identity = self.get_new_uuid()
        if identity not in self.subscribers:
            self.subscribers[identity] = []
        if len(self.subscribers[identity]) <= self.max_subscribers:
            subscriber = self.Subscriber(identity)
            subscriber.set_db_name(self.__db_name)
            subscriber.is_permanent_hear = permanent_hear
            permanent_hear and subscriber.start()  # pylint: disable=W0106
            self.subscribers[identity].append(subscriber)
            return subscriber
        raise ValueError(
            f"Max amount of subscribers ({self.max_subscribers}) was"
            + f" reached for this identity ({identity})"
        )

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
            for subscriber in self.subscribers[identity]:
                if subscriber.is_permanent_hear:
                    subscriber.stop()
                    subscriber.join()  # TODO: Waits for safe termination, if blocking, DELETE
            unsubscribed = self.subscribers[identity]
            del self.subscribers[identity]
            return unsubscribed
        raise ValueError(f"Identity '{identity}' not present in set of subscribers")

    def publish(self, identity: str, topic, value, delay: int = 0):
        """Given an identity, the message is published against the set of subscribers
        liked to this same identity.

        In order to Log information which is published this function requires to use
        the following format:
            identity: Unique UserSession Identity.
            topic: Topic to be used, if logging wants to be done, this must be set to
            'logging'.
            value: Value to be published, if logging wants to be done, this parameter
            needs to be a dictionary structure matching the LogModelORM entity fields
            as dictionary keys.

        Args:
            identity (str): Private identifier of the unique session driving the queries
            against the backend.
            key (str): Context of the information to be published. Can be seen as the ORM model
            definition or serialization as a dictionary of {orm_entity_fields: values}.
            value (any >> __str__): Information to be published. MUST be __str__ serializable!
            delay (int): Amount of seconds of delay to be added to the publish operation.
                Purely DEBUG purposes.
        """
        if identity in self.subscribers:
            time.sleep(delay)
            for subscriber in self.subscribers[identity]:
                subscriber.message = (topic, value)
                subscriber.msg_event.set()
        else:
            self.subscribe(identity)
            self.publish(identity, topic, value)

    def close(self):
        """Closing statement for the ContextBroker entity. It ensures all
        subscribing behaviors get terminated.
        """
        subscribers_keys = copy.deepcopy(list(self.subscribers.keys()))
        for subs_id in subscribers_keys:
            self.unsubscribe(subs_id)

    # pylint: disable=W0238  # Pure DEBUG method, used to configure a testDB
    # in unit and integration tests
    # TODO: __overwrite_db
    def overwrite_db(self, db_name: str) -> None:
        """
        Pure-DEBUG method, it is used to override the current reference
        to the Database. Useful since for Unit and Integration Tests work
        on a secondary Database called "testing".

        Args:
            db_name (str): New reference name of the database.
        """
        self.__db_name = db_name
