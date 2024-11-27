# pylint: disable=C0103
"""
Main module for the logic relative to logging information into de DataBase.

This module is designed to store real time information of the requests and
resources being used by the IAG-LLM application.

Basic functionalities:
    - connect_db
    - create_db
    - insert_log
    - get_log_by_id
    - delete_log_by_id
"""
from abc import ABC, abstractmethod

from src.logger.database import AbstractLogModelORM


class AbstractLogger(ABC):
    """Abstract implementation of a Logger class designed to perform communications
    with the DataBase.

    Args:
        ABC (abc.ABC): Helper class that provides a standard way to create an ABC
        using inheritance.
    """

    def __init__(self, **config):
        for key, value in config.items():
            if hasattr(self, key):
                raise ValueError(
                    f"Attribute name '{key}' clashes with a reserved name or function name."
                )
            setattr(self, key, value)

    @abstractmethod
    def connect_db(self) -> None:
        """
        Performs a connection to the DB selected to run the application on.
        """

    @abstractmethod
    def create_db(self) -> None:
        """
        Base method for generating the Database and its Entities if these ones do
        not exist.

        This call launches against all the [...]ORM.py-like models implementing classes
        inheriting the sqlalchemy.ext.declarative.declarative_base() Base and defining
        a `__tablename__`.
        """

    @abstractmethod
    def insert_log(self, entry: AbstractLogModelORM) -> int:
        """
        Given an instance inheriting the AbstractLogModelORM, it ensures to create and
        store it as a new entry in the DB.

        Args:
            entry (AbstractLogModelORM): Base Logging DB entry for the application.

        Returns:
            int: Unique identifier of a previously created AbstractLogModelORM
            object.
        """

    @abstractmethod
    def get_log_by_id(self, entry_id: int) -> AbstractLogModelORM:
        """
        Given the Identifier (ID) of an instance inheriting the AbstractLogModelORM
        and previously inserted into the DataBase, it ensures to return this same instance
        for being checked or updated.

        Args:
            entry_id (int): Unique identifier of a previously created AbstractLogModelORM
            object.

        Returns:
            AbstractLogModelORM: Base Logging DB entry for the application.
        """

    @abstractmethod
    def get_logs_by_owner(self, owner: str) -> [AbstractLogModelORM]:
        """
        Given the Identifier (ID) of an instance inheriting the AbstractLogModelORM
        and previously inserted into the DataBase, it ensures to return all its request
        sessions.

        Args:
            entry_id (int): Unique identifier of a previously created AbstractLogModelORM
            object.

        Returns:
            AbstractLogModelORM: Base Logging DB entry for the application.
        """

    @abstractmethod
    def delete_log_by_id(self, entry_id: int) -> AbstractLogModelORM:
        """
        Given the Identifier (ID) of an instance inheriting the AbstractLogModelORM
        and previously inserted into the DataBase, it ensures to delete this instance
        from the DB.

        Args:
            entry_id (int): Unique identifier of a previously created AbstractLogModelORM
            object.

        Returns:
            AbstractLogModelORM: Base Logging DB entry for the application.
        """
