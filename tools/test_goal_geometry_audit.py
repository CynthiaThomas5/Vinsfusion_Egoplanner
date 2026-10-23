"""Offline geometry checks, never a flight-approval fixture."""
import math
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parent/'debug_truth'))
from world_geometry import transform,signed_box,signed_cylinder,load_obstacles,distances,segment_bound


class GoalGeometryAuditTests(unittest.TestCase):
    def box(self):
        return [{'name':'box','kind':'box','transform':np.eye(4),'shape':np.array([.001,.5,.5])}]

    def test_signed_distances_include_inside_and_corner(self):
        self.assertTrue(np.allclose(signed_box(np.array([[0,0,0],[2,2,0]]),np.ones(3)),[-1,math.sqrt(2)]))
        self.assertTrue(np.allclose(signed_cylinder(np.array([[0,0,0],[2,0,2]]),1,1),[-1,math.sqrt(2)]))

    def test_pose_composition_uses_rotated_local_axes(self):
        t=transform('2 1 0 0 0 1.5707963267948966')@transform('1 0 0 0 0 0')
        self.assertTrue(np.allclose(t[:3,3],[2,2,0]))

    def test_endpoint_clearance_cannot_miss_thin_intermediate_obstacle(self):
        result=segment_bound([-1,0,0],[1,0,0],self.box(),.1,max_step=2)
        self.assertGreater(result['sampled_nominal_margin_m'],0)
        self.assertFalse(result['static_non_ground_sphere_corridor_clear'])
        self.assertLess(result['continuous_nominal_margin_lower_bound_m'],0)

    def test_clear_corridor_and_zero_length_point(self):
        safe=segment_bound([-1,2,0],[1,2,0],self.box(),.1,max_step=.1)
        self.assertTrue(safe['static_non_ground_sphere_corridor_clear'])
        point=segment_bound([0,0,0],[0,0,0],self.box(),0)
        self.assertEqual(point['sample_cover_radius_m'],0)
        self.assertFalse(point['static_non_ground_sphere_corridor_clear'])

    def test_invalid_segments_fail_closed(self):
        with self.assertRaises(ValueError):distances([[0,0,0]],[])
        for kwargs in [{'radius':-.1},{'radius':.1,'max_step':0},{'radius':.1,'max_step':float('nan')}]:
            with self.assertRaises(ValueError):segment_bound([0,0,0],[1,0,0],self.box(),**kwargs)

    def test_world_loader_cylinder_and_unsupported_frames(self):
        xml='<sdf><world><model name="pillar"><static>true</static><pose>3 0 0 0 0 0</pose><link name="l"><collision name="c"><geometry><cylinder><radius>1</radius><length>4</length></cylinder></geometry></collision></link></model></world></sdf>'
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'world.sdf';p.write_text(xml);obstacles=load_obstacles(p)
            d,n=distances([[3,0,0]],obstacles)
            self.assertEqual(d[0],-1);self.assertEqual(n[0],'pillar/l/c')
            for bad in [xml.replace('<pose>','<pose relative_to="other">'),xml.replace('<static>true</static>','<static>false</static>'),xml.replace('<cylinder>','<mesh>').replace('</cylinder>','</mesh>')]:
                p.write_text(bad)
                with self.assertRaises(ValueError):load_obstacles(p)

    def test_only_explicit_origin_ground_plane_is_omitted(self):
        xml='<sdf><world><model name="wall"><static>true</static><link name="l"><collision name="c"><geometry><plane><normal>0 0 1</normal></plane></geometry></collision></link></model></world></sdf>'
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'world.sdf';p.write_text(xml)
            with self.assertRaises(ValueError):load_obstacles(p)
