import tempfile
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

from n09_contact_evaluation import evaluate_contacts
from prepare_n09_contact_model import D435I, X500_BASE, prepare


class N09ContactOverlayTests(unittest.TestCase):
    @staticmethod
    def collision_signature(node):
        return ET.canonicalize(ET.tostring(node, encoding='unicode'),
                               strip_text=True)

    def test_overlay_covers_all_colliding_vehicle_links_without_geometry_changes(self):
        with tempfile.TemporaryDirectory(prefix='n09-contact-') as temporary:
            output = Path(temporary) / 'models'
            manifest = prepare(output)
            self.assertEqual(len(manifest['sensor_topics']), 6)
            self.assertTrue(manifest['read_only_observation_only'])
            self.assertFalse(manifest['collision_geometry_changed'])
            for source, generated in (
                    (X500_BASE / 'model.sdf', output / 'x500_base/model.sdf'),
                    (D435I / 'model.sdf', output / 'd435i/model.sdf')):
                source_collisions = [self.collision_signature(node) for node in
                                     ET.parse(source).getroot().findall('./model/link/collision')]
                generated_collisions = [self.collision_signature(node) for node in
                                        ET.parse(generated).getroot().findall('./model/link/collision')]
                self.assertEqual(generated_collisions, source_collisions)

    def test_optional_observer_only_adds_wrapper_plugin(self):
        from prepare_n09_contact_model import WRAPPER
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'models'
            manifest = prepare(output, kinematics=True)
            self.assertTrue(manifest['kinematics_observer']['enabled'])
            original = ET.parse(WRAPPER / 'model.sdf').getroot()
            generated = ET.parse(output / 'x500_d435i/model.sdf').getroot()
            model = generated.find('model')
            observer = [p for p in model.findall('plugin')
                        if p.get('name') == 'uav::debug_truth::ModelKinematics']
            self.assertEqual(len(observer), 1)
            model.remove(observer[0])
            self.assertEqual(self.collision_signature(original), self.collision_signature(generated))

    def test_overlay_refuses_reusing_an_existing_path(self):
        with tempfile.TemporaryDirectory(prefix='n09-contact-') as temporary:
            output = Path(temporary) / 'models'
            prepare(output)
            with self.assertRaises(FileExistsError):
                prepare(output)


class N09ContactClassificationTests(unittest.TestCase):
    manifest = {'sensor_topics': ['/n09/contacts/x500/base_link']}
    phases = [
        {'stamp_ns': 10, 'phase': 'TAKEOFF'},
        {'stamp_ns': 20, 'phase': 'ACTIVE'},
        {'stamp_ns': 30, 'phase': 'LANDING'},
        {'stamp_ns': 40, 'phase': 'LANDED'},
    ]

    def report(self, events):
        return {'ready': True, 'expected_topics': self.manifest['sensor_topics'],
                'advertised_topics': self.manifest['sensor_topics'], 'events': events}

    def test_ground_contact_before_goal_and_during_landing_is_allowed(self):
        events = [
            {'topic': self.manifest['sensor_topics'][0], 'stamp_ns': 12,
             'pairs': [{'collision1': 'base_link::body',
                        'collision2': 'ground_plane::link::collision'}]},
            {'topic': self.manifest['sensor_topics'][0], 'stamp_ns': 35,
             'pairs': [{'collision1': 'base_link::body',
                        'collision2': 'ground_plane::link::collision'}]},
        ]
        result = evaluate_contacts(self.report(events), self.manifest,
                                   self.phases, goal_stamp_ns=18)
        self.assertTrue(result['passed'])

    def test_ground_contact_during_active_goal_is_rejected(self):
        events = [{'topic': self.manifest['sensor_topics'][0], 'stamp_ns': 25,
                   'pairs': [{'collision1': 'base_link::body',
                              'collision2': 'ground_plane::link::collision'}]}]
        result = evaluate_contacts(self.report(events), self.manifest,
                                   self.phases, goal_stamp_ns=18)
        self.assertFalse(result['passed'])

    def test_non_ground_vehicle_collision_is_rejected(self):
        events = [{'topic': self.manifest['sensor_topics'][0], 'stamp_ns': 35,
                   'pairs': [{'collision1': 'rotor_0::collision',
                              'collision2': 'blank::Wall_0_Collision'}]}]
        result = evaluate_contacts(self.report(events), self.manifest,
                                   self.phases, goal_stamp_ns=18)
        self.assertFalse(result['passed'])
        self.assertEqual(result['prohibited_contact_event_count'], 1)

    def test_contact_sensors_must_be_advertised_and_touchdown_observed(self):
        result = evaluate_contacts(self.report([]), self.manifest,
                                   self.phases, goal_stamp_ns=18)
        self.assertFalse(result['passed'])
        missing = self.report([])
        missing['advertised_topics'] = []
        result = evaluate_contacts(missing, self.manifest,
                                   self.phases, goal_stamp_ns=18)
        self.assertFalse(result['sensor_topics_ready'])


if __name__ == '__main__':
    unittest.main()
