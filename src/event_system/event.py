from dataclasses import dataclass, field
from datetime import datetime

from .event_type import EventType


@dataclass(frozen=True)
class Event:

    event_type: EventType

    payload: object | None = None

    timestamp: datetime = field(default_factory=datetime.now)