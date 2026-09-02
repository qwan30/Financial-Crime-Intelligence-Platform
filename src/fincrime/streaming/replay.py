from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from fincrime.streaming.events import TransactionEnvelope
from fincrime.streaming.state import ReplayConflict, ReplayState

_HEX64_REGEX = re.compile(r"^[0-9a-f]{64}$")


class BrokerRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    topic: str = Field(min_length=1)
    partition: int = Field(ge=0)
    offset: int = Field(ge=0)
    payload: bytes
    timestamp: datetime

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("topic must not be blank or whitespace-only")
        return v

    @field_validator("timestamp")
    @classmethod
    def validate_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.utcoffset() is None or v.utcoffset() != UTC.utcoffset(v):
            raise ValueError("timestamp must be timezone-aware UTC")
        return v


class QuarantinedRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    topic: str = Field(min_length=1)
    partition: int = Field(ge=0)
    offset: int = Field(ge=0)
    reason: str = Field(min_length=1)
    payload_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    quarantined_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("topic", "reason")
    @classmethod
    def validate_non_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field must not be blank or whitespace-only")
        return v

    @field_validator("payload_hash")
    @classmethod
    def validate_hash(cls, v: str) -> str:
        if not _HEX64_REGEX.match(v):
            raise ValueError(f"payload_hash must be a lowercase 64-character hex string, got '{v}'")
        return v

    @field_validator("quarantined_at")
    @classmethod
    def validate_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.utcoffset() is None or v.utcoffset() != UTC.utcoffset(v):
            raise ValueError("quarantined_at must be timezone-aware UTC")
        return v


class QuarantineStore(Protocol):
    def append(self, record: QuarantinedRecord) -> None: ...
    def get_records(self, topic: str, partition: int) -> list[QuarantinedRecord]: ...


class DurableFileQuarantineStore:
    def __init__(self, storage_dir: str | Path) -> None:
        import threading

        self._dir = Path(storage_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _file_for(self, topic: str, partition: int) -> Path:
        return self._dir / f"quarantine_{topic}_{partition}.jsonl"

    def append(self, record: QuarantinedRecord) -> None:
        path = self._file_for(record.topic, record.partition)
        line = record.model_dump_json() + "\n"
        with self._lock, path.open("a", encoding="utf-8") as f:
            f.write(line)

    def get_records(self, topic: str, partition: int) -> list[QuarantinedRecord]:
        path = self._file_for(topic, partition)
        with self._lock:
            if not path.exists():
                return []
            records: list[QuarantinedRecord] = []
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        records.append(QuarantinedRecord.model_validate_json(line))
            return records


class ReplayOutcome(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    state: ReplayState
    accepted_event_ids: tuple[str, ...]
    quarantined_records: tuple[QuarantinedRecord, ...]
    committable_offsets: tuple[tuple[str, int, int], ...]


def replay_records(
    records: Sequence[BrokerRecord],
    initial_state: ReplayState,
    quarantine_store: QuarantineStore,
) -> ReplayOutcome:
    state = initial_state
    accepted: list[str] = []
    quarantined: list[QuarantinedRecord] = []

    committable: dict[tuple[str, int], int] = {
        (t, p): off for t, p, off in initial_state.partition_offsets
    }
    halted_partitions: set[tuple[str, int]] = set()

    for record in records:
        key = (record.topic, record.partition)
        if key not in committable:
            committable[key] = initial_state.get_offset(record.topic, record.partition)

        if key in halted_partitions:
            continue

        expected_offset = committable[key]
        payload_hash = hashlib.sha256(record.payload).hexdigest().lower()

        # Step 1: Parse envelope
        try:
            event = TransactionEnvelope.model_validate_json(record.payload)
            if event.source_partition != record.partition or event.source_offset != record.offset:
                raise ValueError("Envelope coordinates do not match broker record coordinates")
        except Exception:  # noqa: BLE001
            q_rec = QuarantinedRecord(
                topic=record.topic,
                partition=record.partition,
                offset=record.offset,
                reason="INVALID_SCHEMA",
                payload_hash=payload_hash,
            )
            quarantined.append(q_rec)
            quarantine_store.append(q_rec)
            halted_partitions.add(key)
            continue

        # Step 2: Coordinate-aware duplicate check
        existing_entry = state.get_entry(event.event_id)
        if existing_entry is not None:
            _, ex_topic, ex_part, ex_off, ex_hash = existing_entry
            if (
                ex_topic == record.topic
                and ex_part == record.partition
                and ex_off == record.offset
                and ex_hash == event.canonical_hash()
            ):
                # True no-op: already applied at exact coordinate
                continue
            raise ReplayConflict(
                f"Conflicting retry for event '{event.event_id}': existing ({ex_topic}:{ex_part}@{ex_off}, {ex_hash}) != new ({record.topic}:{record.partition}@{record.offset}, {event.canonical_hash()})"
            )

        # Step 3: Check contiguous cursor for new event
        if record.offset != expected_offset:
            q_rec = QuarantinedRecord(
                topic=record.topic,
                partition=record.partition,
                offset=record.offset,
                reason="NON_CONTIGUOUS_OFFSET",
                payload_hash=payload_hash,
            )
            quarantined.append(q_rec)
            quarantine_store.append(q_rec)
            halted_partitions.add(key)
            continue

        # Step 4: Apply to state and advance committable cursor
        state = state.apply(
            topic=record.topic,
            partition=event.source_partition,
            offset=event.source_offset,
            event_id=event.event_id,
            payload_hash=event.canonical_hash(),
        )
        accepted.append(event.event_id)
        committable[key] = record.offset + 1

    formatted_committable = tuple(
        sorted((topic, part, off) for (topic, part), off in committable.items())
    )

    return ReplayOutcome(
        state=state,
        accepted_event_ids=tuple(accepted),
        quarantined_records=tuple(quarantined),
        committable_offsets=formatted_committable,
    )
