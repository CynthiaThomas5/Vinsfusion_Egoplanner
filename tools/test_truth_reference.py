import copy,json,math,shutil,tempfile,unittest
from pathlib import Path
import numpy as np
from tools.truth_reference import (ROOT,MODEL,CAMERA,BASE,SCHEMA,sha256,
    model_to_imu_contract,convert_model_samples,require_same_truth_reference)

class TruthReferenceTests(unittest.TestCase):
    def sample(self,q=(0,0,0,1)):
        return {'xyz':[1.,2.,3.],'q_xyzw':list(q),'stamp_ns':123,
                'linear_velocity_xyz_m_s':[4,5,6],'angular_velocity_xyz_rad_s':[0,0,1]}

    def test_attitude_rotates_lever_and_input_is_unchanged(self):
        s=self.sample((0,0,math.sqrt(.5),math.sqrt(.5)));before=copy.deepcopy(s)
        row=convert_model_samples([s],[.12,0,.32])[0]
        np.testing.assert_allclose(row['xyz'],[1,2.12,3.32],atol=1e-12)
        self.assertEqual(s,before);self.assertEqual(row['stamp_ns'],123)
        self.assertEqual(row['q_xyzw'],s['q_xyzw'])
        self.assertNotIn('linear_velocity_xyz_m_s',row)
        self.assertNotIn('angular_velocity_xyz_rad_s',row)

    def test_rotation_about_stationary_model_moves_imu_point(self):
        samples=[self.sample(),self.sample((0,0,math.sqrt(.5),math.sqrt(.5)))]
        rows=convert_model_samples(samples,[.12,0,.32])
        self.assertAlmostEqual(np.linalg.norm(np.subtract(rows[1]['xyz'],rows[0]['xyz'])),.12*math.sqrt(2))

    def test_repeated_conversion_is_rejected(self):
        rows=convert_model_samples([self.sample()],[.12,0,.32])
        with self.assertRaisesRegex(ValueError,'already_converted'):
            convert_model_samples(rows,[.12,0,.32])

    def test_invalid_orientation_and_position_rejected(self):
        for q in ((0,0,0,0),(0,0,0,1.1),(float('nan'),0,0,1)):
            with self.assertRaises(ValueError):convert_model_samples([self.sample(q)],[.12,0,.32])
        s=self.sample();s['xyz'][0]=float('inf')
        with self.assertRaises(ValueError):convert_model_samples([s],[.12,0,.32])

    def fixture(self,path):
        root=path/'root';run=path/'run';run.mkdir()
        for name in (MODEL,CAMERA,BASE):
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,p)
        (run/'runtime-contract.json').write_text(json.dumps({'files':{n:sha256(root/n) for n in (MODEL,CAMERA)}}))
        (run/'n09-contact-model-manifest.json').write_text(json.dumps({'source_sha256':{BASE:sha256(root/BASE)}}))
        return root,run

    def test_actual_sdf_chain_resolves_imu_and_does_not_use_frame_label(self):
        with tempfile.TemporaryDirectory() as d:
            root,run=self.fixture(Path(d));contract=model_to_imu_contract(run,root)
            self.assertEqual(contract['model_origin_to_imu_m'],[.12,0,.32])
            self.assertEqual(contract['raw_pose_reference'],'gazebo_model_origin')
            self.assertEqual(contract['source_sha256'][MODEL],sha256(root/MODEL))

    def test_unbound_or_tampered_geometry_is_rejected(self):
        for name in (MODEL,CAMERA,BASE):
            with tempfile.TemporaryDirectory() as d:
                root,run=self.fixture(Path(d));p=root/name;p.write_text(p.read_text()+'\n')
                with self.assertRaises(ValueError):model_to_imu_contract(run,root)

    def test_known_hash_but_publisher_offset_cannot_be_silently_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            root,run=self.fixture(Path(d));p=root/MODEL
            p.write_text(p.read_text().replace('<dimensions>3</dimensions>','<dimensions>3</dimensions><xyz_offset>0 0 .1</xyz_offset>'))
            x=json.loads((run/'runtime-contract.json').read_text());x['files'][MODEL]=sha256(p)
            (run/'runtime-contract.json').write_text(json.dumps(x))
            with self.assertRaisesRegex(ValueError,'offset_requires'):model_to_imu_contract(run,root)

    def test_stale_dependency_report_cannot_be_combined_with_corrected_truth(self):
        c={'schema':SCHEMA,'output_pose_reference':'d435i_imu','model_origin_to_imu_m':[.12,0,.32],'source_sha256':{'a':'1'}}
        with self.assertRaisesRegex(ValueError,'old_or_different'):require_same_truth_reference({},c)
        require_same_truth_reference({'truth_reference_contract':c},c)
        changed=copy.deepcopy(c);changed['model_origin_to_imu_m'][2]=.08
        with self.assertRaises(ValueError):require_same_truth_reference({'truth_reference_contract':changed},c)

class PrestreamAnchorTests(unittest.TestCase):
    def test_arrival_anchor_matches_raw_vio_prestream_anchor(self):
        from tools.truth_reference import fixed_prestream_alignment
        with tempfile.TemporaryDirectory() as directory:
            run=Path(directory)
            raw=[{'kind':'raw_odom','source_ns':t,'xyz':[t/1e9,0,0],
                  'q_xyzw':[0,0,0,1],'frame_id':'vins_e_world','child_frame_id':'vins_e_imu'}
                 for t in (880_000_000,900_000_000,1_100_000_000)]
            (run/'alignment-observation.json').write_text(json.dumps({
                'epoch':'e','raw_topic':'/vins_raw/s_e/odometry','samples':raw}))
            (run/'bridge-alignment-timeline.jsonl').write_text(json.dumps({'phase':'PRESTREAM','stamp_ns':1_000_000_000})+'\n')
            truth=[{'stamp_ns':t,'xyz':[4+t/1e9,0,.3],'q_xyzw':[0,0,0,1]}
                   for t in (880_000_000,900_000_000,920_000_000,1_100_000_000)]
            rotation,translation,anchor=fixed_prestream_alignment(run,truth)
            np.testing.assert_allclose(rotation,np.eye(3));np.testing.assert_allclose(translation,[4,0,.3])
            self.assertEqual(anchor['reference_source_ns'],900_000_000)
            raw[0]['frame_id']='foreign_world'
            (run/'alignment-observation.json').write_text(json.dumps({'epoch':'e','raw_topic':'/vins_raw/s_e/odometry','samples':raw}))
            with self.assertRaisesRegex(ValueError,'frame_or_epoch'):
                fixed_prestream_alignment(run,truth)


class AcceptanceReferenceBindingTests(unittest.TestCase):
    def test_mixed_legacy_and_corrected_reports_cannot_pass_binding(self):
        from unittest import mock
        from tools.debug_truth.evaluate_n10_acceptance import truth_reference_evidence
        contract={'schema': SCHEMA, 'output_pose_reference': 'd435i_imu',
                  'model_origin_to_imu_m': [.12,0,.32], 'source_sha256': {'model':'hash'},
                  'conversion_tool_sha256': 'conversion-hash'}
        with tempfile.TemporaryDirectory() as directory:
            run=Path(directory)
            names=('arrival-evaluation-simtime-v2.json','odometry-evaluation.json',
                   'n10-vins-velocity-evaluation.json','n10-tracking-clearance-relation.json',
                   'n10-clearance-evaluation.json','n10-interval-clearance-bound.json')
            for name in names:(run/name).write_text(json.dumps({'truth_reference_contract':contract}))
            metrics={'truth_reference_contract':contract}
            with mock.patch('truth_reference.model_to_imu_contract',return_value=contract):
                self.assertEqual(truth_reference_evidence(metrics,run)['status'],'PASS')
                (run/'odometry-evaluation.json').write_text('{}')
                result=truth_reference_evidence(metrics,run)
                self.assertEqual(result['status'],'INSUFFICIENT')
                self.assertIn('odometry-evaluation.json',result['report_mismatches'])
                result=truth_reference_evidence({},run)
                self.assertEqual(result['status'],'INSUFFICIENT')


if __name__=='__main__':unittest.main()
