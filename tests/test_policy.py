import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from awayke import policy as p  # noqa: E402


class AutoOff(unittest.TestCase):
    def d(self, **kw):
        base = dict(intent=True, suspended=False, percent=50, on_ac=False, threshold=20)
        base.update(kw)
        return p.decide(**base)

    def test_threshold_zero_disables(self): self.assertEqual(self.d(percent=5, threshold=0), p.NONE)
    def test_suspend_below(self): self.assertEqual(self.d(percent=19), p.SUSPEND)
    def test_no_suspend_at_threshold(self): self.assertEqual(self.d(percent=20), p.NONE)
    def test_no_suspend_on_ac(self): self.assertEqual(self.d(percent=5, on_ac=True), p.NONE)
    def test_no_suspend_intent_off(self): self.assertEqual(self.d(percent=5, intent=False), p.NONE)
    def test_resume(self): self.assertEqual(self.d(suspended=True, percent=25, on_ac=True), p.RESUME)
    def test_no_resume_in_band(self): self.assertEqual(self.d(suspended=True, percent=24, on_ac=True), p.NONE)
    def test_no_resume_on_battery(self): self.assertEqual(self.d(suspended=True, percent=30), p.NONE)
    def test_override_blocks_suspend(self): self.assertEqual(self.d(percent=5, overridden=True), p.NONE)
    def test_override_allows_resume(self):
        self.assertEqual(self.d(suspended=True, percent=25, on_ac=True, overridden=True), p.RESUME)
    def test_override_keep(self):
        self.assertTrue(p.should_keep_override(True, False))
        self.assertFalse(p.should_keep_override(True, True))
        self.assertFalse(p.should_keep_override(False, False))


class LidSession(unittest.TestCase):
    def test_open_start(self):
        t = p.LidSessionTracker(); t.start(False)
        self.assertTrue(t.is_waiting_for_close)
        self.assertFalse(t.handle(False))
        self.assertFalse(t.handle(True))
        self.assertFalse(t.is_waiting_for_close)
        self.assertTrue(t.handle(False))
        self.assertFalse(t.handle(False))

    def test_closed_start(self):
        t = p.LidSessionTracker(); t.start(True)
        self.assertTrue(t.handle(False))

    def test_cancelled(self):
        t = p.LidSessionTracker(); t.start(False); t.cancel()
        self.assertFalse(t.handle(True)); self.assertFalse(t.handle(False))

    def test_unknown_start(self):
        t = p.LidSessionTracker(); t.start(None)
        self.assertTrue(t.is_waiting_for_close)
        self.assertFalse(t.handle(True)); self.assertTrue(t.handle(False))


if __name__ == "__main__":
    unittest.main()
