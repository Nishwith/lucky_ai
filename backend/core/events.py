import asyncio
from typing import Callable, List, Dict, Any, Awaitable
from backend.core.logger import logger

# Async event handler type signature
EventHandler = Callable[[Any], Awaitable[None]]

class EventBus:
    def __init__(self):
        self._listeners: Dict[str, List[EventHandler]] = {}

    def on(self, event_name: str, handler: EventHandler):
        """Register an async handler for a given event name."""
        if event_name not in self._listeners:
            self._listeners[event_name] = []
        self._listeners[event_name].append(handler)
        logger.debug(f"Registered event listener for: {event_name}")

    async def emit(self, event_name: str, data: Any = None):
        """Emit an event, executing all registered handlers concurrently."""
        if event_name not in self._listeners:
            return
        
        logger.debug(f"Emitting event '{event_name}' with data: {data}")
        tasks = []
        for handler in self._listeners[event_name]:
            tasks.append(asyncio.create_task(self._safe_execute(handler, event_name, data)))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_execute(self, handler: EventHandler, event_name: str, data: Any):
        try:
            await handler(data)
        except Exception as e:
            logger.error(f"Unhandled error in event handler for '{event_name}': {e}", exc_info=True)

# Global singleton event bus
event_bus = EventBus()
