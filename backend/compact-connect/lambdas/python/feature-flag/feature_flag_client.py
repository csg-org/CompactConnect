from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass


@dataclass
class FeatureFlagContext:
    """Context information for feature flag evaluation"""
    user_id: Optional[str] = None
    environment: str = 'prod'
    custom_attributes: Optional[Dict[str, Any]] = None


@dataclass 
class FeatureFlagResult:
    """Result of a feature flag check"""
    enabled: bool
    flag_name: str
    metadata: Optional[Dict[str, Any]] = None


class FeatureFlagClient(ABC):
    """
    Abstract base class for feature flag clients.
    
    This interface provides a consistent way to interact with different
    feature flag providers (StatSig, LaunchDarkly, etc.) while hiding
    the underlying implementation details.
    """
    
    @abstractmethod
    def check_flag(self, flag_name: str, context: FeatureFlagContext) -> FeatureFlagResult:
        """
        Check if a feature flag is enabled for the given context.
        
        :param flag_name: Name of the feature flag to check
        :param context: Context for flag evaluation (environment, user, etc.)
        :return: FeatureFlagResult indicating if flag is enabled
        :raises FeatureFlagException: If flag check fails
        """
        pass