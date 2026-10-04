import logging
from typing import Dict, Any, List
from .base import BaseResolver
from .mugisubs import MugiSubsResolver
from .kiyoshii import KiyoshiiResolver
from .generic import GenericResolver

logger = logging.getLogger("resolver_hub")

class ResolverHub:
    def __init__(self):
        self.resolvers: List[BaseResolver] = [
            MugiSubsResolver(),
            KiyoshiiResolver(),
            GenericResolver() # Fallback
        ]

    async def resolve(self, url: str) -> Dict[str, Any]:
        url = url.strip()
        for resolver in self.resolvers:
            if resolver.can_handle(url):
                try:
                    logger.info(f"Using resolver '{resolver.name}' for URL: {url[:60]}")
                    res = await resolver.resolve(url)
                    res["resolver_used"] = resolver.name
                    return res
                except Exception as e:
                    logger.warning(f"Resolver '{resolver.name}' failed: {e}. Trying fallback...")
                    if isinstance(resolver, GenericResolver):
                        raise
        
        # Last resort
        generic = GenericResolver()
        res = await generic.resolve(url)
        res["resolver_used"] = generic.name
        return res

hub = ResolverHub()
