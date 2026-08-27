import io
import unittest
from contextlib import redirect_stdout

from enterprise_programming.cli import main


class CommandLineTests(unittest.TestCase):
    def run_command(self, arguments):
        output = io.StringIO()
        with redirect_stdout(output):
            result = main(arguments)
        self.assertEqual(result, 0)
        return output.getvalue()

    def test_sensor_demo_reports_processed_total(self):
        output = self.run_command(
            ["sensor-demo", "--sensors", "2", "--readings", "3", "--workers", "1"]
        )
        self.assertIn("Processed 6 readings with 1 worker", output)
        self.assertIn("sensor-01", output)
        self.assertIn("sensor-02", output)

    def test_sensor_demo_uses_singular_labels(self):
        output = self.run_command(
            ["sensor-demo", "--sensors", "1", "--readings", "1", "--workers", "1"]
        )
        self.assertIn("Processed 1 reading with 1 worker", output)

    def test_task_demo_completes_workflow(self):
        output = self.run_command(["task-demo"])
        self.assertIn("changed from pending to in_progress", output)
        self.assertIn("2 tasks tracked; 1 completed", output)


if __name__ == "__main__":
    unittest.main()
