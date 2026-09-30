"""Stdlib tests for calendar_write_mcp.py argument hardening.

Run from this folder:  python -m unittest test_calendar_write_mcp
gog is replaced by a fake that prints its argv as JSON, so nothing touches Google.
"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import calendar_write_mcp as mcp  # noqa: E402

FAKE_GOG = "import json, sys\nprint(json.dumps(sys.argv[1:]))\n"


class CalendarWriteArgTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        path = os.path.join(cls.tmp.name, "fake_gog.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write(FAKE_GOG)
        cls.saved = (mcp.GOG_CMD, mcp.ACCOUNT, mcp.CALENDAR)
        mcp.GOG_CMD = [sys.executable, path]
        mcp.ACCOUNT = "automation@example.com"
        mcp.CALENDAR = "primary"

    @classmethod
    def tearDownClass(cls):
        mcp.GOG_CMD, mcp.ACCOUNT, mcp.CALENDAR = cls.saved
        cls.tmp.cleanup()

    def call(self, name, args):
        try:
            return mcp.HANDLERS[name](args)
        except mcp.BadArgs as e:
            return False, f"invalid arguments: {e}"

    def argv(self, name, args):
        ok, out = self.call(name, args)
        self.assertTrue(ok, out)
        return json.loads(out)

    def test_injection_example_rejected(self):
        ok, out = self.call("calendar_update_event",
                            {"event_id": "--attendees=x@y.z", "summary": "-v"})
        self.assertFalse(ok)
        self.assertIn("event_id", out)

    def test_dash_values_stay_values(self):
        argv = self.argv("calendar_update_event", {"event_id": "abc123_20260101", "summary": "-v"})
        self.assertIn("--summary=-v", argv)
        self.assertNotIn("-v", argv)
        argv = self.argv("calendar_create_event", {
            "summary": "--attendees=x@y.z", "start": "2026-06-27T09:00:00+00:00",
            "end": "2026-06-27T10:00:00+00:00", "location": "--delete"})
        self.assertIn("--summary=--attendees=x@y.z", argv)
        self.assertIn("--location=--delete", argv)
        self.assertFalse(any(a.startswith("--attendees") for a in argv))
        self.assertNotIn("--delete", argv)

    def test_non_string_rejected(self):
        ok, out = self.call("calendar_create_event",
                            {"summary": ["-v"], "start": "a", "end": "b"})
        self.assertFalse(ok)
        ok, out = self.call("calendar_create_event",
                            {"summary": "x", "start": "a", "end": "b", "all_day": "yes"})
        self.assertFalse(ok)
        ok, out = self.call("calendar_update_event", {"event_id": 123, "summary": "x"})
        self.assertFalse(ok)

    def test_newline_rejected_outside_description(self):
        ok, _ = self.call("calendar_update_event", {"event_id": "abc", "summary": "a\n--v"})
        self.assertFalse(ok)
        argv = self.argv("calendar_update_event", {"event_id": "abc", "description": "line1\nline2"})
        self.assertIn("--description=line1\nline2", argv)

    def test_no_delete_tool(self):
        self.assertEqual(sorted(mcp.HANDLERS), ["calendar_create_event", "calendar_update_event"])


if __name__ == "__main__":
    unittest.main()
