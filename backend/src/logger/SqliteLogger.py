# pylint: disable=C0103
"""
Main module for the logic relative to logging information into de DataBase.

This module is designed to store real time information of the requests and
resources being used by the IAG-LLM application.

Basic functionalities:
    - connect_db
    - disconnect_db
    - create_db
    - insert_log
    - get_log_by_id
    - delete_log_by_id
"""

import os
import shutil

from os import sep
from typing import List

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.orm.exc import NoResultFound

from src.logger.AbstractLogger import AbstractLogger
from src.logger.database import Base, DocumentSnippetORM, LogModelORM


class SqliteLogger(AbstractLogger):
    """Abstract implementation of a Logger class designed to perform communications
    with the DataBase.

    Args:
        ABC (abc.ABC): Helper class that provides a standard way to create an ABC
        using inheritance.
    """

    BASE_DB_PATH = "./databases/logs_db"
    DB_NAME = "analytics"
    engine = None
    session = None

    def __init__(self, db_path=None, db_name=DB_NAME, **config):
        super().__init__(**config)
        self.db_path = self.BASE_DB_PATH if db_path is None else db_path
        self.db_name = self.DB_NAME if db_name is None else db_name + ".db"
        self.connect_db()
        self.create_db()

    def connect_db(self) -> None:
        """
        Performs a connection to the DB selected to run the application on.
        """
        os.makedirs(self.db_path, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{self.db_path + sep + self.db_name}")
        self.session = scoped_session(sessionmaker(bind=self.engine))

    def disconnect_db(self) -> None:
        """
        Performs a disconnection to the DB selected to run the application on.
        """
        if self.session is None:
            raise ValueError(
                "Unexpected behavior reached! Be sure to connect_db() "
                + "before disconnect_db()!"
            )
        self.session.close()
        self.session.remove()

    def create_db(self) -> None:
        """
        Base method for generating the Database and its Entities if these ones do
        not exist.

        This call launches against all the [...]ORM.py-like models implementing classes
        inheriting the sqlalchemy.ext.declarative.declarative_base() Base and defining
        a `__tablename__`.
        """
        if self.engine is None:
            raise ValueError(
                "Unexpected behavior reached! Be sure to connect_db() "
                + "before create_db()!"
            )
        engine = self.engine
        Base.metadata.create_all(engine)

    def insert_log(self, entry: LogModelORM) -> int:
        """
        Given an instance inheriting the AbstractLogModelORM, it ensures to create and
        store it as a new entry in the DB.

        Args:
            entry (AbstractLogModelORM): Base Logging DB entry for the application.

        Returns:
            int: Unique identifier of a previously created AbstractLogModelORM
            object.
        """
        self.__prove_tablename_set()

        if entry.id is not None:
            existing_entry = (
                self.session.query(LogModelORM).filter_by(id=entry.id).first()
            )
            if existing_entry:
                raise ValueError(
                    f"Log entry with ID {entry.id} already exists"
                    + ", update it instead!"
                )

        try:
            self.session.add(entry)
            self.session.commit()
            return entry.id
        except IntegrityError as exc:
            self.session.rollback()
            raise ValueError(
                "IntegrityError: Potential duplicate or constraint violation."
            ) from exc
        except OperationalError as exc:
            self.session.rollback()
            raise ConnectionError(
                "ConnectionError: Check database connection or permissions."
            ) from exc
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise RuntimeError(f"Unhandled  Database error occurred: {exc}") from exc
        finally:
            self.session.close()

    def get_log_by_id(self, entry_id: int) -> LogModelORM:
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
        self.__prove_tablename_set()
        analytic = self.session.query(LogModelORM).filter_by(id=entry_id).first()
        self.session.close()
        if analytic:
            return analytic
        raise NoResultFound(
            f"Table '{LogModelORM.__tablename__}' does not contain an entry with"
            + f" the ID provided '{entry_id}'!"
        )

    def get_log_by_owner(self, owner: str) -> LogModelORM:
        """
        Given the unique UserIdentifier (UID) of an application user, it returns the most
        recent open (status==1) interaction with the DataBase. If there is no open interaction,
        it raises a NoResultFound.

        Args:
            owner (int): Owner UserID-unique identifier.

        Returns:
            AbstractLogModelORM: Base Logging DB entry for the application.

        Raises:
            NoResultFound: If no entity was found for the retrieval.
        """
        self.__prove_tablename_set()
        analytic = (
            self.session.query(LogModelORM)
            .filter_by(owner=owner, status=1)
            .order_by(LogModelORM.start_time.desc())
            .first()
        )

        self.session.close()
        if analytic:
            return analytic
        raise NoResultFound(
            f"Table '{LogModelORM.__tablename__}' does not contain an open entry"
            + f" (status==1) for the owner provided '{owner}'!"
        )

    def get_logs_by_owner(self, owner: str) -> [LogModelORM]:
        """
        Given the UserIdentifier (owner) of an instance inheriting the AbstractLogModelORM
        with registers previously inserted into the DataBase, it ensures to return all its
        request sessions.

        Args:
            entry_id (int): Unique identifier of a previously created AbstractLogModelORM
            object.

        Returns:
            AbstractLogModelORM: Base Logging DB entry for the application.
        """
        self.__prove_tablename_set()
        analytics = (
            self.session.query(LogModelORM)
            .filter_by(owner=owner)
            .order_by(LogModelORM.start_time.desc())
        ).all()

        self.session.close()
        if analytics:
            return analytics
        raise NoResultFound(
            f"Table '{LogModelORM.__tablename__}' does not contain any entry"
            + f"for the owner provided '{owner}'!"
        )

    def update_log_by_id(self, entry_id: int, **updated_fields) -> None:
        """
        Update an existing log entry with the given fields.

        Args:
            entry_id (int): The ID of the log entry to be updated.
            **updated_fields: Arbitrary keyword arguments of the fields to update.

        Raises:
            NoResultFound: If the log entry with the given ID does not exist.
            ValueError: If an integrity issue is encountered (e.g., duplicate).
            ConnectionError: If there are issues with the database connection.
            RuntimeError: For any other unexpected database errors.
        """
        self.__prove_tablename_set()
        try:
            entry = self.session.query(LogModelORM).filter_by(id=entry_id).first()
            if not entry:
                raise NoResultFound(
                    f"Entry with ID {entry_id} not found in table LogModelORM"
                )

            # If end_time is specified to be updated, the whole conversation has
            # ended, no more stats will be provided
            if "end_time" in updated_fields:
                entry.status = 0

            for key, value in updated_fields.items():
                if hasattr(entry, key):
                    setattr(entry, key, value)

            self.session.commit()
        except NoResultFound as exc:
            raise exc
        except IntegrityError as exc:
            self.session.rollback()
            raise ValueError(
                "IntegrityError: Potential duplicate or constraint violation."
            ) from exc
        except OperationalError as exc:
            self.session.rollback()
            raise ConnectionError(
                "ConnectionError: Check database connection or permissions."
            ) from exc
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise RuntimeError(f"Unhandled database error occurred: {exc}") from exc
        finally:
            self.session.close()

    def update_document_by_log_id_and_doc_id(
        self, log_id: str, doc_id: str, updated_fields: dict
    ) -> None:
        """
        Update a specific document associated with a given log ID and document ID.

        Args:
            log_id (int): The ID of the log entry.
            doc_id (str): The ID of the document to be updated.
            updated_fields (dict): A dictionary of fields to be updated.

        Raises:
            NoResultFound: If the document with the given ID does not exist.
            SQLAlchemyError: For any database errors.
        """
        self.__prove_tablename_set()
        try:
            document = (
                self.session.query(DocumentSnippetORM)
                .filter_by(id=doc_id, parent_id=log_id)
                .first()
            )
            if not document:
                raise NoResultFound(
                    f"Document with ID {doc_id} not found in table DocumentSnippetORM"
                )

            for key, value in updated_fields.items():
                if hasattr(document, key):
                    setattr(document, key, value)

            self.session.commit()
        except NoResultFound as exc:
            raise exc
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise RuntimeError(f"Unhandled database error occurred: {exc}") from exc
        finally:
            self.session.close()

    def update_document_by_log_id_and_doc_href(
        self, log_id: int, doc_href: str, updated_fields: dict
    ) -> None:
        """
        Update a specific document associated with a given log ID and document href.

        Args:
            log_id (int): The ID of the log entry.
            doc_href (str): The href of the document to be updated.
            updated_fields (dict): A dictionary of fields to be updated.

        Raises:
            NoResultFound: If the document with the given href does not exist.
            SQLAlchemyError: For any database errors.
        """
        self.__prove_tablename_set()
        try:
            document = (
                self.session.query(DocumentSnippetORM)
                .filter_by(href=doc_href, parent_id=log_id)
                .first()
            )
            if not document:
                raise NoResultFound(
                    f"Document with href {doc_href} not found in table DocumentSnippetORM"
                )

            for key, value in updated_fields.items():
                if hasattr(document, key):
                    setattr(document, key, value)

            self.session.commit()
        except NoResultFound as exc:
            raise exc
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise RuntimeError(f"Unhandled database error occurred: {exc}") from exc
        finally:
            self.session.close()

    def delete_log_by_id(self, entry_id: int) -> LogModelORM:
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
        self.__prove_tablename_set()
        analytic = self.session.query(LogModelORM).filter_by(id=entry_id).first()
        if not analytic:
            raise NoResultFound(
                f"Table '{LogModelORM.__tablename__}' does not contain an entry with"
                + f" the ID provided '{entry_id}'!"
            )
        self.session.delete(analytic)
        self.session.commit()
        self.session.close()
        return analytic

    def delete_document_by_log_id_and_doc_id(self, log_id: int, doc_id: str) -> None:
        """
        Delete a specific document associated with a given log ID and document ID.

        Args:
            log_id (int): The ID of the log entry.
            doc_id (str): The ID of the document to be deleted.

        Raises:
            NoResultFound: If the document with the given ID does not exist.
            SQLAlchemyError: For any database errors.
        """
        self.__prove_tablename_set()
        try:
            document = (
                self.session.query(DocumentSnippetORM)
                .filter_by(id=doc_id, parent_id=log_id)
                .first()
            )
            if not document:
                raise NoResultFound(
                    f"Document with ID {doc_id} not found in table DocumentSnippetORM"
                )

            self.session.delete(document)
            self.session.commit()
        except NoResultFound as exc:
            raise exc
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise RuntimeError(f"Unhandled database error occurred: {exc}") from exc
        finally:
            self.session.close()

    def get_documents_by_log_id(self, log_id: str):
        """
        Retrieve all documents snippets (important chunks retrieved) associated with a
        given log ID or LLM Answer.

        Args:
            log_id (int): The ID of the log entry.

        Returns:
            List[DocumentSnippetORM]: A list of DocumentSnippetORM objects.
        """
        self.__prove_tablename_set()
        documents = (
            self.session.query(DocumentSnippetORM).filter_by(parent_id=log_id).all()
        )
        self.session.close()
        return documents

    def get_document_by_log_id_and_doc_id(
        self, log_id: int, doc_id: str
    ) -> DocumentSnippetORM:
        """
        Retrieve a specific document associated with a given log ID and document ID.

        Args:
            log_id (int): The ID of the log entry.
            doc_id (str): The ID of the document to be retrieved.

        Returns:
            DocumentSnippetORM: The document snippet ORM object.

        Raises:
            NoResultFound: If the document with the given ID does not exist.
            SQLAlchemyError: For any database errors.
        """
        self.__prove_tablename_set()
        try:
            document = (
                self.session.query(DocumentSnippetORM)
                .filter_by(id=doc_id, parent_id=log_id)
                .first()
            )
            if not document:
                raise NoResultFound(
                    f"Document with ID {doc_id} not found in table DocumentSnippetORM"
                )
            return document
        except SQLAlchemyError as exc:
            raise RuntimeError(f"Unhandled database error occurred: {exc}") from exc
        finally:
            self.session.close()

    def insert_document_by_log_id(self, log_id: int, document: dict) -> None:
        """
        Insert a single document associated with a given log ID.

        Args:
            log_id (int): The ID of the log entry.
            document (dict): A dictionary containing document data. The fields of this
            dictionary can be inspected in src/logger/database.py DocumentSnippetORM
            class definition.
        """
        self.__prove_tablename_set()
        try:
            document["parent_id"] = log_id
            new_doc = DocumentSnippetORM(**document)
            self.session.add(new_doc)
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise RuntimeError(f"Unhandled database error occurred: {exc}") from exc
        finally:
            self.session.close()

    def insert_documents_by_log_id(self, log_id: str, documents: List[dict]) -> None:
        """
        Insert multiple documents associated with a given log ID.

        Args:
            log_id (str): The ID of the log entry.
            documents (List[dict]): A list of dictionaries containing document data.
        """
        self.__prove_tablename_set()
        for doc_data in documents:
            self.insert_document_by_log_id(log_id, doc_data)

    def is_doc_id_in_log_documents(self, log_id: int, doc_id: str) -> bool:
        """
        Check if a document with the given ID exists in the documents of a log entry.

        Args:
            log_id (int): The ID of the log entry.
            doc_id (str): The ID of the document to check.

        Returns:
            bool: True if the document exists, False otherwise.
        """
        self.__prove_tablename_set()
        try:
            document = (
                self.session.query(DocumentSnippetORM)
                .filter_by(id=doc_id, parent_id=log_id)
                .first()
            )
            return document is not None
        except SQLAlchemyError as exc:
            raise RuntimeError(f"Unhandled database error occurred: {exc}") from exc
        finally:
            self.session.close()

    def is_doc_href_in_log_documents(self, log_id: int, doc_href: str) -> bool:
        """
        Check if there is any document associated with a given log ID that
        has the specified href.

        Args:
            log_id (int): The ID of the log entry.
            doc_href (str): The href of the document to check.

        Returns:
            bool: True if a document with the given href exists, False
            otherwise.
        """
        self.__prove_tablename_set()
        try:
            document = (
                self.session.query(DocumentSnippetORM)
                .filter_by(href=doc_href, parent_id=log_id)
                .first()
            )
            return document is not None
        except SQLAlchemyError as exc:
            raise RuntimeError(f"Unhandled database error occurred: {exc}") from exc
        finally:
            self.session.close()

    def __prove_tablename_set(self) -> None:
        """
        Proves if the Main table of the LLM-IAG does contain all the required fields.

        Raises:
            ValueError: Exception raised if the table is missing the '__tablename__'
            attribute.
        """
        if not hasattr(LogModelORM, "__tablename__"):
            raise ValueError(
                "Table 'LogModelORM' being accessed was not correctly initialized. "
                + "Missing '__tablename__' attribute!"
            )

    # pylint: disable=W0238 # Pure-DEBUG method
    def __remove_db(self, not_found_ok=False) -> None:
        """
        Pure DEBUG-Based method to handle e2e tests. It allows to complete delete the
        current instance of the DataBase and all its tables.

        For security reasons this method is forced to make a copy called:
        `db_path + '_old'` in which a copy of the database will be kept meanwhile
        the original `db_path` will be removed allowing to test again the
        create_db() functionality.

        Raises:
            FileNotFoundError: If no previous database was created.
        """
        db_filepath = self.db_path + sep + self.db_name

        if os.path.exists(db_filepath):
            filename = db_filepath.split(".db")[0]
            backup_path = f"{filename}_old.db"
            if os.path.exists(backup_path):
                os.remove(backup_path)
            shutil.copyfile(db_filepath, backup_path)
            os.remove(db_filepath)
        elif not not_found_ok:
            raise FileNotFoundError(
                f"No database '{self.db_name}' was found under location: '{self.db_path}'"
            )
