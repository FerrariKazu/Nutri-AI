from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Generator, AsyncGenerator

class LLMClient(ABC):
    """Abstract Base Class for LLM Backends"""

    @abstractmethod
    def health_check(self) -> Dict:
        """Return system health info"""
        pass

    @abstractmethod
    def stream_text(
        self,
        messages: List[Dict],
        max_new_tokens: int = 2048,
        temperature: float = 0.3
    ) -> Generator[str, None, None]:
        """Synchronous or Async Generator for streaming tokens"""
        pass

    @abstractmethod
    def generate_text(
        self,
        messages: List[Dict],
        max_new_tokens: int = 4096,
        temperature: float = 0.7,
        json_mode: bool = False,
        stream_callback: Optional[callable] = None
    ) -> str:
        """Generate full text response"""
        pass
