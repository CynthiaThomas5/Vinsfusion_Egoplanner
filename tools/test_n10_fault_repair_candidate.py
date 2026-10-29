import ast
import json
import math
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from test_px4_bridge_control import supervisor, ready_snapshot
from test_localization_health import body_velocity
from uav_localization.health import quaternion_diagnostic

ROOT=Path(__file__).resolve().parents[1]

class FaultRepairTests(unittest.TestCase):
    def test_descend_does_not_confirm_old_accepted_land(self):
        m=supervisor(retry_limit=2); m.phase=m.ACTIVE
        s=ready_snapshot(armed=True,landed=False,px4_descend_active=True,
                         px4_landing_active=True,land_command_accepted=True)
        self.assertEqual(m.disable(s,0).command,'land')
        self.assertEqual(m.step(s,.5).command,'')
        self.assertEqual(m.step(s,1).command,'land')
        output=m.step(s,2)
        self.assertIn('native_descend_requires_operator',output.reason)
        self.assertEqual(output.phase,m.LANDING)
        self.assertEqual(output.command,'')
        self.assertFalse(output.publish_offboard)
        s.update(landed=True,armed=False)
        self.assertEqual(m.step(s,3).phase,m.LANDED)

    def test_auto_land_confirmation_stops_retries(self):
        m=supervisor();m.phase=m.ACTIVE
        s=ready_snapshot(armed=True,landed=False,px4_landing_active=True,
                         px4_descend_active=False)
        self.assertEqual(m.disable(s,0).command,'')
        self.assertEqual(m.step(s,10).phase,m.LANDING)
        self.assertEqual(m.land_command_attempts,0)

    def test_rejected_quaternion_is_logged_and_still_faults(self):
        path=ROOT/'src/own/uav_localization/uav_localization/node.py'
        klass=next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.ClassDef))
        method=next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name=='on_raw')
        space=dict(math=math,json=json,body_velocity=body_velocity,
                   quaternion_diagnostic=quaternion_diagnostic,stamp_ns=lambda h: h.stamp)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),str(path),'exec'),space)
        logs=[];faults=[]
        node=NS(bind=lambda k:True,raw_world='world',raw_body='imu',epoch='epoch-a',
                published={'optimized':10,'propagated':11},imu=[(12,[0,0,0])],
                health=NS(clock_ns=20),fault=faults.append,
                get_logger=lambda:NS(error=logs.append))
        msg=NS(header=NS(frame_id='world',stamp=19),child_frame_id='imu',
               pose=NS(pose=NS(position=NS(x=0,y=0,z=0),orientation=NS(x=0,y=0,z=0,w=1.02))),
               twist=NS(twist=NS(linear=NS(x=0,y=0,z=0))))
        space['on_raw'](node,'propagated',msg)
        self.assertEqual(faults,['propagated_invalid_quaternion'])
        record=json.loads(logs[0].split(' ',1)[1])
        self.assertEqual(record['quaternion_xyzw'],[0,0,0,1.02])
        self.assertEqual(record['source_stamp_ns'],19)
        self.assertEqual(msg.pose.pose.orientation.w,1.02)

    def test_diagnostic_serializes_nonfinite_without_accepting_it(self):
        record=quaternion_diagnostic([math.nan,0,0,1])
        json.dumps(record,allow_nan=False)
        self.assertIsNone(record['quaternion_norm'])
        with self.assertRaises(ValueError):body_velocity([0,0,0,1.02],[0,0,0])

if __name__=='__main__': unittest.main()
