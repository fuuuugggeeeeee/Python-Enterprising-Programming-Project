"""Concurrent sensor-reading aggregation."""

from __future__ import annotations

import math
import queue
import random
import threading
import time
from dataclasses import dataclass
from typing import Dict, Iterable, Iterator, List, Optional


@dataclass(frozen=True)
class SensorReading:
    """A single observation produced by a sensor."""

    sensor_id: str
    value: float
    observed_at: float

    def __post_init__(self) -> None:
        if not self.sensor_id.strip():
            raise ValueError("sensor_id must not be empty")
        if not math.isfinite(self.value):
            raise ValueError("value must be a finite number")
        if not math.isfinite(self.observed_at):
            raise ValueError("observed_at must be a finite timestamp")


@dataclass(frozen=True)
class SensorStatistics:
    """An immutable statistics snapshot for one sensor."""

    count: int
    minimum: float
    maximum: float
    average: float

    def as_dict(self) -> Dict[str, float]:
        return {
            "count": self.count,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "average": self.average,
        }


@dataclass
class _Accumulator:
    count: int = 0
    total: float = 0.0
    minimum: float = math.inf
    maximum: float = -math.inf

    def add(self, value: float) -> None:
        self.count += 1
        self.total += value
        self.minimum = min(self.minimum, value)
        self.maximum = max(self.maximum, value)

    def snapshot(self) -> SensorStatistics:
        return SensorStatistics(
            count=self.count,
            minimum=self.minimum,
            maximum=self.maximum,
            average=self.total / self.count,
        )


class SensorAggregator:
    """Aggregate readings safely across a fixed pool of worker threads.

    The lifecycle is explicit: call :meth:`start`, submit readings, then call
    :meth:`stop`. Using the object as a context manager performs those steps
    automatically.
    """

    _STOP = object()

    def __init__(self, worker_count: int = 4) -> None:
        if worker_count < 1:
            raise ValueError("worker_count must be at least 1")

        self._worker_count = worker_count
        self._queue: "queue.Queue[object]" = queue.Queue()
        self._condition = threading.Condition(threading.RLock())
        self._statistics: Dict[str, _Accumulator] = {}
        self._threads: List[threading.Thread] = []
        self._accepted = 0
        self._processed = 0
        self._running = False
        self._accepting = False
        self._closed = False

    @property
    def accepted_count(self) -> int:
        with self._condition:
            return self._accepted

    @property
    def processed_count(self) -> int:
        with self._condition:
            return self._processed

    def start(self) -> "SensorAggregator":
        with self._condition:
            if self._closed:
                raise RuntimeError("a stopped aggregator cannot be restarted")
            if self._running:
                return self

            self._running = True
            self._accepting = True
            self._threads = [
                threading.Thread(
                    target=self._worker,
                    name="sensor-worker-{}".format(index + 1),
                    daemon=True,
                )
                for index in range(self._worker_count)
            ]
            for thread in self._threads:
                thread.start()
        return self

    def submit(self, reading: SensorReading) -> None:
        if not isinstance(reading, SensorReading):
            raise TypeError("reading must be a SensorReading")

        with self._condition:
            if not self._accepting:
                raise RuntimeError("aggregator is not accepting readings")
            self._accepted += 1
            self._queue.put(reading)

    def wait_until_processed(self, timeout: Optional[float] = None) -> bool:
        """Wait for everything accepted at call time; return False on timeout."""

        with self._condition:
            target = self._accepted
            return self._condition.wait_for(
                lambda: self._processed >= target,
                timeout=timeout,
            )

    def snapshot(self) -> Dict[str, SensorStatistics]:
        with self._condition:
            return {
                sensor_id: accumulator.snapshot()
                for sensor_id, accumulator in sorted(self._statistics.items())
            }

    def stop(self, timeout: Optional[float] = None) -> None:
        with self._condition:
            if not self._running:
                self._closed = True
                self._accepting = False
                return
            self._accepting = False

        if not self.wait_until_processed(timeout=timeout):
            raise TimeoutError("timed out while processing sensor readings")

        for _ in self._threads:
            self._queue.put(self._STOP)

        deadline = None if timeout is None else time.monotonic() + timeout
        for thread in self._threads:
            remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
            thread.join(remaining)
            if thread.is_alive():
                raise TimeoutError("timed out while stopping sensor workers")

        with self._condition:
            self._running = False
            self._closed = True

    def _worker(self) -> None:
        while True:
            item = self._queue.get()
            try:
                if item is self._STOP:
                    return
                reading = item
                if not isinstance(reading, SensorReading):
                    continue
                with self._condition:
                    accumulator = self._statistics.setdefault(
                        reading.sensor_id,
                        _Accumulator(),
                    )
                    accumulator.add(reading.value)
                    self._processed += 1
                    self._condition.notify_all()
            finally:
                self._queue.task_done()

    def __enter__(self) -> "SensorAggregator":
        return self.start()

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.stop()


def generate_readings(
    sensor_count: int = 3,
    readings_per_sensor: int = 100,
    seed: int = 42,
) -> Iterator[SensorReading]:
    """Generate deterministic sample readings for demos and load tests."""

    if sensor_count < 1:
        raise ValueError("sensor_count must be at least 1")
    if readings_per_sensor < 1:
        raise ValueError("readings_per_sensor must be at least 1")

    randomizer = random.Random(seed)
    timestamp = time.time()
    for reading_index in range(readings_per_sensor):
        for sensor_index in range(sensor_count):
            baseline = 20.0 + sensor_index * 5.0
            yield SensorReading(
                sensor_id="sensor-{:02d}".format(sensor_index + 1),
                value=round(randomizer.normalvariate(baseline, 1.5), 3),
                observed_at=timestamp + reading_index / 10.0,
            )


def process_readings(
    readings: Iterable[SensorReading],
    worker_count: int = 4,
) -> Dict[str, SensorStatistics]:
    """Convenience function that processes a finite iterable of readings."""

    with SensorAggregator(worker_count=worker_count) as aggregator:
        for reading in readings:
            aggregator.submit(reading)
    return aggregator.snapshot()
