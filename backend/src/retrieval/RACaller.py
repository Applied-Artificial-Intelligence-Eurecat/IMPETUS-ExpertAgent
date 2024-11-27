# pylint: disable=C0103
"""
Specific implementation of the call() methodology linked to the RetrievalAugmented procedure.
"""

from typing import List

from .AbstractRA import AbstractRA, DocumentObject


# pylint: disable=R0903
class RACaller:
    """
    A utility class designed to interface with an instance of AbstractRA to facilitate the process
    of retrieval augmentation. This class abstracts the complexity of invoking the retrieval
    augmentation logic contained within an AbstractRA instance, simplifying the user interaction.

    Attributes:
        RA (AbstractRA): An instance of AbstractRA that performs document retrieval augmentation.
    """

    def __init__(self, RA: AbstractRA):
        """
        Initializes the RACaller with a specific instance of AbstractRA.

        Args:
            RA (AbstractRA): An instance of the retrieval augmentation class that adheres to the
            AbstractRA interface.
        """
        self.RA = RA

    def __call__(self, optimized_query: str, query_id) -> List[DocumentObject]:
        """
        Aggregates document references using the provided AbstractRA instance based on an optimized
        query. This method abstracts the aggregation process, allowing for easy integration of
        document reference aggregation capabilities in various applications.

        Args:
            optimized_query (str): The optimized query used to aggregate relevant document objects.

        Returns:
            List[DocumentObject]: A list of DocumentObject instances aggregated based on the
            optimized query.
        """
        return self.RA(optimized_query, query_id)
