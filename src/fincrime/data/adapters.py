from __future__ import annotations

from typing import ClassVar

import polars as pl


class AMLSimAdapter:
    mapping: ClassVar[dict[str, str]] = {
        "transaction_id": "edge_id",
        "orig_id": "source_id",
        "dest_id": "target_id",
        "amount": "amount",
        "timestamp": "event_time",
    }

    def transactions(self, frame: pl.DataFrame) -> pl.DataFrame:
        missing = tuple(sorted(set(self.mapping) - set(frame.columns)))
        if missing:
            raise ValueError(f"missing source columns: {missing}")
        return frame.select(
            [pl.col(source).alias(target) for source, target in self.mapping.items()]
        )


class AMLBenchAdapter:
    mapping: ClassVar[dict[str, str]] = {
        "transaction_id": "edge_id",
        "source_account_id": "source_id",
        "target_account_id": "target_id",
        "amount": "amount",
        "transaction_time": "event_time",
    }

    def transactions(self, frame: pl.DataFrame) -> pl.DataFrame:
        missing = tuple(sorted(set(self.mapping) - set(frame.columns)))
        if missing:
            raise ValueError(f"missing source columns: {missing}")
        return frame.select(
            [pl.col(source).alias(target) for source, target in self.mapping.items()]
        )
