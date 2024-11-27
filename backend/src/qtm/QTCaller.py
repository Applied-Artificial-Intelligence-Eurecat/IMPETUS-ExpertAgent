from . import Answer
from . import AbstractQT

class QTCaller:
    """
    A utility class designed to interface with an instance of AbstractQT to transform user queries. This class
    simplifies the use of query transformers by encapsulating the details of invoking the transformation logic
    contained within an AbstractQT instance.

    Attributes:
        QT (AbstractQT): An instance of AbstractQT that performs query transformations.
    """
    def __init__(self, QT: AbstractQT) -> None:
        """
        Initializes the QTCaller with a specific instance of AbstractQT.

        Args:
            QT (AbstractQT): An instance of the query transformer class that adheres to the AbstractQT interface.
        """
        self.QT = QT

    def __call__(self, user_query: str, query_id) -> Answer:
        """
        Transforms a user query using the provided AbstractQT instance and returns the transformed result. This
        method abstracts the transformation process, allowing for simple integration of query transformation
        capabilities in various applications.

        Args:
            user_query (str): The user's query to be transformed by the QT instance.

        Returns:
            Answer: The result of the query transformation, encapsulated in an Answer object which may include
            additional information like the response's metadata or context.
        """
        return self.QT(user_query, query_id)
