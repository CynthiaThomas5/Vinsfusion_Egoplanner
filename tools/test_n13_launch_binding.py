import json
from pathlib import Path
import tempfile
import unittest
from tools.debug_truth.evaluate_n13_run import launch_protocol_bound,sha

class LaunchBindingTests(unittest.TestCase):
    def test_historical_binding_requires_exact_record_and_protocol(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);run=root/'run';run.mkdir();release=root/'release.json';release.write_text('{}')
            launch={'protocol_sha256':'old'};record=run/'n13-launch-record.json';record.write_text(json.dumps(launch))
            policy={'authorized_reassessments':{'run':{'basis':'evidence_processing_fix_no_runtime_or_numeric_change','launch_record_sha256':sha(record),'original_protocol_sha256':'old'}}}
            self.assertTrue(launch_protocol_bound(run,launch,policy,release))
            record.write_text('{}')
            self.assertFalse(launch_protocol_bound(run,launch,policy,release))

    def test_other_run_cannot_reuse_historical_permission(self):
        with tempfile.TemporaryDirectory() as d:
            run=Path(d)/'other';run.mkdir();release=Path(d)/'release.json';release.write_text('{}')
            self.assertFalse(launch_protocol_bound(run,{'protocol_sha256':'old'},{'authorized_reassessments':{}},release))
