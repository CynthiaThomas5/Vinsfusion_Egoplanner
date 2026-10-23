import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from recover_preflight_fixture import _persisted_attachment_is_current


class PersistedAttachmentTests(unittest.TestCase):
    def fixture_report(self):
        return {
            'attachment_states': ['attached'],
            'fixture_may_remain_attached': True,
            'fixture_removed': False,
            'n05_live_check_completed': False,
        }

    def test_last_attached_state_is_usable_only_while_model_and_run_state_agree(self):
        self.assertTrue(_persisted_attachment_is_current(
            self.fixture_report(), fixture_present=True,
            release_marker_exists=False, scanner_running=False))

    def test_release_or_scanner_activity_invalidates_persisted_state(self):
        for release, scanner in ((True, False), (False, True)):
            self.assertFalse(_persisted_attachment_is_current(
                self.fixture_report(), fixture_present=True,
                release_marker_exists=release, scanner_running=scanner))

    def test_removed_or_not_attached_report_cannot_authorize_recovery_motion(self):
        report=self.fixture_report();report['fixture_removed']=True
        self.assertFalse(_persisted_attachment_is_current(
            report, True, False, False))
        report=self.fixture_report();report['attachment_states']=['detached']
        self.assertFalse(_persisted_attachment_is_current(
            report, True, False, False))


if __name__ == '__main__':
    unittest.main()
