from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseResolver(ABC):
    name: str = "Base"

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Return True if this resolver can handle the given URL."""
        pass

    @abstractmethod
    async def resolve(self, url: str) -> Dict[str, Any]:
        """
        Resolve URL into downloadable item(s).
        Returns dict with:
        {
            "type": "single" | "batch",
            "title": str,
            "items": [
                {
                    "name": str,
                    "url": str,
                    "size": int (optional),
                    "size_formatted": str (optional),
                    "headers": dict (optional)
                }
            ]
        }
        """
        pass
