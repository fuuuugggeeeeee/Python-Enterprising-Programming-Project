import math
import unittest

from enterprise_programming.sensor import (
    SensorAggregator,
    SensorReading,
    generate_readings,
    process_readings,
)


class SensorReadingTests(unittest.TestCase):
    def test_rejects_empty_sensor_id(self):
        with self.assertRaises(ValueError):
            SensorReading(" ", 1.0, 10.0)

    def test_rejects_non_finite_values(self):
        with self.assertRaises(ValueError):
            SensorReading("sensor-1", math.inf, 10.0)


class SensorAggregatorTests(unittest.TestCase):
    def test_aggregates_exact_statistics(self):
        readings = [
            SensorReading("temperature", 10.0, 1.0),
            SensorReading("temperature", 20.0, 2.0),
            SensorReading("humidity", 60.0, 3.0),
        ]
        result = process_readings(readings, worker_count=2)
        self.assertEqual(result["temperature"].count, 2)
        self.assertEqual(result["temperature"].minimum, 10.0)
        self.assertEqual(result["temperature"].maximum, 20.0)
        self.assertEqual(result["temperature"].average, 15.0)
        self.assertEqual(result["humidity"].average, 60.0)

    def test_processes_all_readings_concurrently(self):
        readings = list(generate_readings(10, 250, seed=7))
        aggregator = SensorAggregator(worker_count=8).start()
        for reading in readings:
            aggregator.submit(reading)
        self.assertTrue(aggregator.wait_until_processed(timeout=5.0))
        aggregator.stop(timeout=5.0)
        self.assertEqual(aggregator.accepted_count, 2_500)
        self.assertEqual(aggregator.processed_count, 2_500)
        self.assertEqual(sum(item.count for item in aggregator.snapshot().values()), 2_500)

    def test_enforces_lifecycle(self):
        aggregator = SensorAggregator()
        reading = SensorReading("sensor-1", 1.0, 1.0)
        with self.assertRaises(RuntimeError):
            aggregator.submit(reading)
        aggregator.start()
        aggregator.submit(reading)
        aggregator.stop()
        with self.assertRaises(RuntimeError):
            aggregator.submit(reading)
        with self.assertRaises(RuntimeError):
            aggregator.start()

    def test_validates_generator_arguments(self):
        with self.assertRaises(ValueError):
            list(generate_readings(sensor_count=0))
        with self.assertRaises(ValueError):
            list(generate_readings(readings_per_sensor=0))


if __name__ == "__main__":
    unittest.main()
