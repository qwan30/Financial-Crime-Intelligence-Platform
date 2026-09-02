from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

_HEX64_REGEX = re.compile(r"^[0-9a-f]{64}$")


class ReplayConflict(RuntimeError):
    """Raised when an event ID conflicts or offset sequence is non-contiguous."""


class ReplayState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    # Stored as immutable sorted tuples: ((event_id, topic, partition, offset, payload_hash), ...)
    event_entries: tuple[tuple[str, str, int, int, str], ...] = Field(default_factory=tuple)
    partition_offsets: tuple[tuple[str, int, int], ...] = Field(default_factory=tuple)

    @field_validator("event_entries")
    @classmethod
    def validate_entries(
        cls, v: tuple[tuple[str, str, int, int, str], ...]
    ) -> tuple[tuple[str, str, int, int, str], ...]:
        seen_events: set[str] = set()
        for item in v:
            if not isinstance(item, tuple) or len(item) != 5:
                raise ValueError(
                    "Each event entry must be a 5-tuple (event_id, topic, partition, offset, payload_hash)"
                )
            event_id, topic, partition, offset, h = item
            if not isinstance(event_id, str) or not event_id.strip():
                raise ValueError("event_id must not be blank")
            if not isinstance(topic, str) or not topic.strip():
                raise ValueError("topic must not be blank")
            if not isinstance(partition, int) or partition < 0:
                raise ValueError("partition must be a non-negative integer")
            if not isinstance(offset, int) or offset < 0:
                raise ValueError("offset must be a non-negative integer")
            if not isinstance(h, str) or not _HEX64_REGEX.match(h):
                raise ValueError(f"Invalid lowercase SHA-256 hash '{h}' for event '{event_id}'")
            if event_id in seen_events:
                raise ValueError(f"Duplicate event_id '{event_id}' in ReplayState entries")
            seen_events.add(event_id)
        if v != tuple(sorted(v, key=lambda x: x[0])):
            raise ValueError("event_entries must be sorted by event_id")
        return v

    @field_validator("partition_offsets")
    @classmethod
    def validate_offsets(
        cls, v: tuple[tuple[str, int, int], ...]
    ) -> tuple[tuple[str, int, int], ...]:
        seen_keys: set[tuple[str, int]] = set()
        for item in v:
            if not isinstance(item, tuple) or len(item) != 3:
                raise ValueError(
                    "Each partition offset must be a 3-tuple (topic, partition, offset)"
                )
            topic, partition, off = item
            if not isinstance(topic, str) or not topic.strip():
                raise ValueError("topic must not be blank")
            if not isinstance(partition, int) or partition < 0:
                raise ValueError("partition must be a non-negative integer")
            if not isinstance(off, int) or off < 0:
                raise ValueError("offset must be a non-negative integer")
            key = (topic, partition)
            if key in seen_keys:
                raise ValueError(f"Duplicate topic-partition key '{key}' in ReplayState offsets")
            seen_keys.add(key)
        if v != tuple(sorted(v, key=lambda x: (x[0], x[1]))):
            raise ValueError("partition_offsets must be sorted by (topic, partition)")
        return v

    @classmethod
    def empty(cls) -> ReplayState:
        return cls(event_entries=(), partition_offsets=())

    def get_entry(self, event_id: str) -> tuple[str, str, int, int, str] | None:
        for entry in self.event_entries:
            if entry[0] == event_id:
                return entry
        return None

    def get_hash(self, event_id: str) -> str | None:
        entry = self.get_entry(event_id)
        return entry[4] if entry is not None else None

    def get_offset(self, topic: str, partition: int) -> int:
        for t, p, off in self.partition_offsets:
            if t == topic and p == partition:
                return off
        return 0

    def apply(
        self,
        topic: str,
        partition: int,
        offset: int,
        event_id: str,
        payload_hash: str,
    ) -> ReplayState:
        if not isinstance(topic, str) or not topic.strip():
            raise ValueError("topic must not be blank")
        if not isinstance(event_id, str) or not event_id.strip():
            raise ValueError("event_id must not be blank")
        if not isinstance(partition, int) or partition < 0:
            raise ValueError("partition must be a non-negative integer")
        if not isinstance(offset, int) or offset < 0:
            raise ValueError("offset must be a non-negative integer")
        if not isinstance(payload_hash, str) or not _HEX64_REGEX.match(payload_hash):
            raise ValueError(
                f"Invalid payload hash: must be lowercase 64-hex string, got '{payload_hash}'"
            )

        existing_entry = self.get_entry(event_id)
        current_offset = self.get_offset(topic, partition)

        if existing_entry is not None:
            _, ex_topic, ex_part, ex_off, ex_hash = existing_entry
            if (
                ex_topic == topic
                and ex_part == partition
                and ex_off == offset
                and ex_hash == payload_hash
            ):
                return self
            raise ReplayConflict(
                f"Conflicting retry for event '{event_id}': existing ({ex_topic}:{ex_part}@{ex_off}, {ex_hash}) != new ({topic}:{partition}@{offset}, {payload_hash})"
            )

        if offset != current_offset:
            raise ReplayConflict(
                f"Non-contiguous offset on {topic}:{partition}: expected {current_offset}, got {offset}"
            )

        new_entries = {e[0]: e for e in self.event_entries}
        new_entries[event_id] = (event_id, topic, partition, offset, payload_hash)

        new_offsets = {(t, p): off for t, p, off in self.partition_offsets}
        new_offsets[(topic, partition)] = offset + 1

        # Direct model construction to enforce all Pydantic validators on transitions
        return ReplayState(
            event_entries=tuple(sorted(new_entries.values(), key=lambda x: x[0])),
            partition_offsets=tuple(sorted((t, p, off) for (t, p), off in new_offsets.items())),
        )
