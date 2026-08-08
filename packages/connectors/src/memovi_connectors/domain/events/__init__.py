"""Connector domain events.

Event types will be added when connectors publish durable sync/import facts on
the platform event bus. The filesystem connector currently returns results
synchronously without publishing domain events.
"""

__all__: list[str] = []
