"""Unit tests for snapper snapshot helpers."""

import json
import subprocess
import unittest
from unittest.mock import MagicMock, patch

from mast.core.snapshots import (
    SnapshotEntry,
    build_snapshot_create_command,
    build_snapshot_delete_command,
    build_snapshot_list_command,
    list_snapshots,
    parse_snapshots_from_json,
)


class TestSnapshots(unittest.TestCase):
    @patch("mast.core.snapshots.snapshots.subprocess.run")
    def test_list_snapshots_sorted_desc(self, mock_run: MagicMock) -> None:
        payload = [
            {
                "number": 10,
                "type": "single",
                "date": "2026-07-10 10:00:00",
                "user": "root",
                "description": "Before update",
                "cleanup": "number",
            },
            {
                "number": 12,
                "type": "single",
                "date": "2026-07-11 09:00:00",
                "user": "root",
                "description": "After update",
                "cleanup": "number",
            },
        ]
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(payload))

        snapshots = list_snapshots()

        self.assertEqual([item.number for item in snapshots], [12, 10])
        self.assertEqual(snapshots[0].description, "After update")

    @patch("mast.core.snapshots.snapshots.subprocess.run")
    def test_list_snapshots_parses_used_space(self, mock_run: MagicMock) -> None:
        payload = [
            {
                "number": 10,
                "type": "single",
                "date": "2026-07-10 10:00:00",
                "user": "root",
                "used-space": 1536,
                "description": "Before update",
                "cleanup": "number",
            },
        ]
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(payload))

        snapshots = list_snapshots()

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].used_space, 1536)

    @patch("mast.core.snapshots.snapshots.subprocess.run")
    def test_list_snapshots_supports_dict_payload(self, mock_run: MagicMock) -> None:
        payload = {
            "snapshots": [
                {
                    "id": "5",
                    "type": "single",
                    "timestamp": "2026-07-11 10:00:00",
                    "user": "root",
                    "description": "Test",
                    "cleanup": "timeline",
                }
            ]
        }
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(payload))

        snapshots = list_snapshots(config="home")

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].number, 5)
        self.assertEqual(snapshots[0].date, "2026-07-11 10:00:00")
        mock_run.assert_called_once_with(
            ["pkexec", "snapper", "-c", "home", "--jsonout", "list"],
            capture_output=True,
            text=True,
            check=True,
            timeout=None,
        )

    def test_build_create_command(self) -> None:
        command = build_snapshot_create_command("Before migration")
        self.assertEqual(
            command,
            ["pkexec", "snapper", "-c", "root", "create", "--description", "Before migration"],
        )

    def test_build_delete_command(self) -> None:
        command = build_snapshot_delete_command(42)
        self.assertEqual(command, ["pkexec", "snapper", "-c", "root", "delete", "42"])

    def test_build_create_command_rejects_empty_description(self) -> None:
        with self.assertRaises(ValueError):
            build_snapshot_create_command("   ")

    def test_build_delete_command_rejects_non_positive(self) -> None:
        with self.assertRaises(ValueError):
            build_snapshot_delete_command(0)

    def test_build_list_command_default_config(self) -> None:
        command = build_snapshot_list_command()
        self.assertEqual(command, ["pkexec", "snapper", "-c", "root", "--jsonout", "list"])

    def test_build_list_command_custom_config(self) -> None:
        command = build_snapshot_list_command(config="home")
        self.assertEqual(command, ["pkexec", "snapper", "-c", "home", "--jsonout", "list"])

    def test_parse_snapshots_from_json_list_payload(self) -> None:
        payload = json.dumps([
            {"number": 10, "type": "single", "date": "2026-07-10 10:00:00", "user": "root", "description": "Before", "cleanup": "number"},
            {"number": 12, "type": "single", "date": "2026-07-11 09:00:00", "user": "root", "description": "After", "cleanup": "number"},
        ])
        snapshots = parse_snapshots_from_json(payload)
        self.assertEqual(len(snapshots), 2)
        self.assertEqual([s.number for s in snapshots], [12, 10])
        self.assertEqual(snapshots[0].description, "After")

    def test_parse_snapshots_from_json_dict_payload(self) -> None:
        payload = json.dumps({
            "snapshots": [
                {"id": "5", "type": "single", "timestamp": "2026-07-11 10:00:00", "user": "root", "used-space": 2097152, "description": "Test", "cleanup": "timeline"},
            ]
        })
        snapshots = parse_snapshots_from_json(payload)
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].number, 5)
        self.assertEqual(snapshots[0].date, "2026-07-11 10:00:00")
        self.assertEqual(snapshots[0].used_space, 2097152)

    def test_parse_snapshots_from_json_empty_string(self) -> None:
        snapshots = parse_snapshots_from_json("")
        self.assertEqual(snapshots, [])

    def test_parse_snapshots_from_json_malformed_json(self) -> None:
        with self.assertRaises(json.JSONDecodeError):
            parse_snapshots_from_json("invalid json")

    def test_parse_snapshots_from_json_config_key_format(self) -> None:
        payload = json.dumps({
            "root": [
                {"number": 10, "type": "single", "date": "2026-07-10 10:00:00", "user": "root", "description": "Before", "cleanup": "number"},
                {"number": 12, "type": "single", "date": "2026-07-11 09:00:00", "user": "root", "description": "After", "cleanup": "number"},
            ]
        })
        snapshots = parse_snapshots_from_json(payload)
        self.assertEqual(len(snapshots), 2)
        self.assertEqual([s.number for s in snapshots], [12, 10])

if __name__ == "__main__":
    unittest.main()
