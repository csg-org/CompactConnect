from abc import abstractmethod
from enum import Enum


class CCEnum(Enum):
    """
    Base class for Compact Connect enums

    We are using this class to ensure that all enums have a from_str method for consistency.
    This pattern gives us flexibility to add additional mapping logic in the future if needed.
    """

    @staticmethod
    @abstractmethod
    def from_str(label: str) -> 'CCEnum':
        pass
