"""Evidence coverage tests; fixture results never count as flight evidence."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from tools.n11_acceptance_contract import evaluate, scene_check

ROOT = Path(__file__).resolve().parents[1]
WORLD = ROOT / 'simulation/worlds/ego.sdf'

class ContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.run = self.base / 'run'; self.run.mkdir()
        self.frozen = self.base / 'frozen'; self.frozen.mkdir()
        self.config = ROOT / 'config/acceptance.json'
        self.protocol = self.base / 'protocol.json'
        fixture_policy=json.loads((ROOT / 'docs/protocols/n11-empty-scene.json').read_text())
        fixture_policy.update(status='preparation',runtime_match_mode='legacy_scene_only',acceptance_config_sha256=hashlib.sha256(self.config.read_bytes()).hexdigest())
        self.protocol.write_text(json.dumps(fixture_policy))
        self.world = self.run / 'vio_initialization.sdf'
        tree=ET.parse(WORLD); world=tree.getroot().find('world')
        for model in list(world.findall('model')):
            if model.get('name','').startswith('unit_cylinder'): world.remove(model)
        tree.write(self.world)
        policy=json.loads(self.protocol.read_text())
        self.scene_hash=policy['scene_source_sha256']
        self.write(self.frozen, 'runtime-contract.json', {'sha256':policy['frozen_runtime_contract_sha256'], 'files':{'simulation/worlds/ego.sdf':'old_scene'}})
        self.current={'sha256':'new', 'files':{'simulation/worlds/ego.sdf':self.scene_hash}}
        self.write(self.run,'runtime-contract.json',self.current)
        self.write(self.run,'world.json',{'project_geometry_sha256':self.scene_hash,'output_sha256':hashlib.sha256(self.world.read_bytes()).hexdigest()})
        self.write(self.run,'n11-launch-record.json',{'scenario':'empty_room','world_mutation_commands':[],'runtime_contract_sha256':'new','protocol_sha256':hashlib.sha256(self.protocol.read_bytes()).hexdigest(),'map_id':'map'})
    def write(self,d,name,data): (d/name).write_text(json.dumps(data))
    def check(self): return evaluate(self.run,self.frozen,self.config,self.protocol)
    def test_exact_release_rejects_runtime_drift(self):
        policy=json.loads(self.protocol.read_text());policy['runtime_match_mode']='exact_released_runtime'
        self.protocol.write_text(json.dumps(policy))
        self.assertIn('runtime_differs_from_released_baseline',self.check()['failures'])
    def test_exact_release_accepts_identical_runtime(self):
        policy=json.loads(self.protocol.read_text());policy['runtime_match_mode']='exact_released_runtime'
        self.protocol.write_text(json.dumps(policy))
        policy['frozen_runtime_contract_sha256']='new';self.protocol.write_text(json.dumps(policy))
        self.write(self.frozen,'runtime-contract.json',self.current)
        self.assertNotIn('runtime_differs_from_released_baseline',self.check()['failures'])
    def test_preparation_cannot_count(self):
        r=self.check();self.assertFalse(r['formal_count_eligible']);self.assertIn('recording_and_evaluation_pipeline_not_released',r['insufficient'])
    def test_missing_flight_is_insufficient(self): self.assertIn('flight_missing',self.check()['insufficient'])
    def test_extra_runtime_change_is_failure(self):
        self.current['files']['tools/controller.py']='bad';self.write(self.run,'runtime-contract.json',self.current)
        self.assertIn('runtime_changes_exceed_declared_scene',self.check()['failures'])
    def test_world_must_match_provenance(self):
        self.world.write_text(self.world.read_text()+'\n')
        self.assertIn('active_world_provenance_mismatch',self.check()['failures'])
    def test_empty_room_has_four_walls(self): self.assertTrue(scene_check(self.world)[0])
    def test_added_model_is_rejected(self):
        tree=ET.parse(self.world);ET.SubElement(tree.getroot().find('world'),'model',{'name':'hidden_obstacle'});tree.write(self.world)
        self.assertFalse(scene_check(self.world)[0])
    def test_include_is_rejected(self):
        tree=ET.parse(self.world);ET.SubElement(tree.getroot().find('world'),'include');tree.write(self.world)
        self.assertFalse(scene_check(self.world)[0])
    def test_dynamic_wall_is_rejected(self):
        tree=ET.parse(self.world);tree.getroot().find("world/model[@name='blank']/static").text='false';tree.write(self.world)
        self.assertFalse(scene_check(self.world)[0])
    def test_dynamic_fail_is_never_suppressed(self):
        self.write(self.run,'n10-acceptance-evaluation.json',{'metrics':[{'id':'dynamic_replanning','status':'FAIL'}]})
        self.assertIn('observed_failure:dynamic_replanning',self.check()['failures'])
    def test_duplicates_are_not_last_write_wins(self):
        self.write(self.run,'n10-acceptance-evaluation.json',{'metrics':[{'id':'arrival_position_yaw_dwell','status':'FAIL'},{'id':'arrival_position_yaw_dwell','status':'PASS'}]})
        self.assertIn('duplicate_metric_rows',self.check()['failures'])
    def test_frozen_config_identity_is_required(self):
        other=self.base/'config.json';d=json.loads(self.config.read_text());d['metrics']['arrival_position_yaw_dwell']['thresholds']['position_error_max_m']=9;other.write_text(json.dumps(d))
        self.assertIn('frozen_acceptance_config_mismatch',evaluate(self.run,self.frozen,other,self.protocol)['failures'])
    def test_common_report_failure_is_preserved(self):
        self.write(self.run,'n10-acceptance-evaluation.json',{'overall_status':'FAIL','metrics':[]})
        self.assertIn('common_evaluation_failed',self.check()['failures'])
    def test_unrelated_failure_does_not_change_event_applicability(self):
        self.write(self.run,'n10-acceptance-evaluation.json',{'metrics':[{'id':'resource_and_queue_behavior','status':'FAIL'},{'id':'dynamic_replanning','status':'INSUFFICIENT'}]})
        result=self.check()
        self.assertIn('observed_failure:resource_and_queue_behavior',result['failures'])
        self.assertEqual(next(m['status'] for m in result['metrics'] if m['id']=='dynamic_replanning'),'NOT_APPLICABLE')
    def test_missing_gui_evidence_is_insufficient(self):
        self.assertIn('visible_gui_evidence_missing_or_mismatched',self.check()['insufficient'])
    def test_missing_independent_terminal_is_insufficient(self):
        self.assertIn('independent_safe_terminal_not_verified',self.check()['insufficient'])
    def test_false_gui_flags_are_rejected(self):
        self.write(self.run,'gui-windows.json',{'run_id':self.run.name,'gazebo_window_present':False,'rviz_window_present':True})
        self.assertIn('visible_gui_evidence_missing_or_mismatched',self.check()['insufficient'])
    def test_missing_map_evidence_cannot_pass(self): self.assertIn('static_wall_map_evaluation_missing',self.check()['insufficient'])

if __name__ == '__main__': unittest.main()
