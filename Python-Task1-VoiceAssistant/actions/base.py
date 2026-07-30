"""
Base Action module defining the interface for all Voice Assistant actions.
"""

from abc import ABC, abstractmethod

class BaseAction(ABC):
    """
    Abstract Base Class for all assistant actions.
    Enforces a consistent execution interface.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """The identifier name of the action (matches NLU intent)."""
        pass

    @abstractmethod
    def execute(self, entities: dict) -> dict:
        """
        Executes the action logic.
        
        Args:
            entities (dict): Extracted entities/slots from the NLU parser.
            
        Returns:
            dict: {
                "speech": str,       # Text feedback for TTS and chat UI
                "ui_data": dict      # Structured data to send to the Web UI dashboard
            }
        """
        pass
