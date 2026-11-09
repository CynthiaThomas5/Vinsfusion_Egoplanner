"""Hardware endpoint caching keeps periodic publisher-change lockout active."""
from pathlib import Path
from types import SimpleNamespace
import sys,time,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/own/uav_localization'))
from uav_localization.node import Localization

class EndpointCacheTests(unittest.TestCase):
    def node(self,hardware=True,changed=False):
        calls=[];faults=[]
        endpoint=SimpleNamespace(endpoint_gid=list(range(1,25)) if changed else list(range(24)),node_name='vins',node_namespace='/vins')
        n=SimpleNamespace(hardware_mode=hardware,health=SimpleNamespace(locked=False,state='INITIALIZING'),gids={},vins_node=None,topics={'propagated':'/vins/odom'},pending={},last_age_log_wall=time.monotonic())
        n.get_publishers_info_by_topic=lambda topic:(calls.append(topic) or [endpoint])
        def fault(reason):faults.append(reason);n.health.locked=True
        n.fault=fault;n.advance_hardware_clock=lambda:True;n.drain=lambda:None;n.status=lambda:None
        return n,calls,faults,endpoint
    def test_hardware_reuses_binding_between_status_checks(self):
        n,c,_,_=self.node()
        self.assertTrue(Localization.bind(n,'propagated'))
        for _ in range(100):self.assertTrue(Localization.bind(n,'propagated'))
        self.assertEqual(len(c),1)
    def test_simulation_still_checks_every_message(self):
        n,c,_,_=self.node(False)
        for _ in range(3):self.assertTrue(Localization.bind(n,'propagated'))
        self.assertEqual(len(c),3)
    def test_timer_locks_changed_cached_publisher_even_during_startup(self):
        for state in ('INITIALIZING','TRACKING'):
            n,c,f,e=self.node();Localization.bind(n,'propagated')
            n.health.state=state;e.endpoint_gid=list(range(1,25))
            Localization.on_timer(n)
            self.assertTrue(n.health.locked)
            self.assertEqual(f,['propagated_publisher_missing_or_changed'])
            self.assertEqual(len(c),2)


class OwnedOdometryTests(unittest.TestCase):
    def test_hardware_consumes_once_and_simulation_keeps_raw_object(self):
        import math
        from nav_msgs.msg import Odometry
        for hardware in (True,False):
            messages=[];msg=Odometry();msg.header.stamp.sec=1
            msg.header.frame_id='raw';msg.child_frame_id='raw_body'
            msg.pose.pose.orientation.z=math.sqrt(.5);msg.pose.pose.orientation.w=math.sqrt(.5)
            msg.twist.twist.linear.x=1.
            health=SimpleNamespace(locked=False,clock_ns=1000000000,last_pair=1000000000,
                paired=lambda *a,**kw:True,enforce_freshness=lambda *a:True,tick=lambda wall:True)
            n=SimpleNamespace(hardware_mode=hardware,health=health,pending={'propagated':msg},
                published={'propagated':None},counts={'propagated':0},require_solver_usable=True,
                world='odom_epoch',body='imu_epoch',advance_hardware_clock=lambda:True,
                angular_velocity=lambda stamp:[.1,.2,.3],
                output={'propagated':SimpleNamespace(publish=messages.append)})
            Localization.drain(n);Localization.drain(n)
            self.assertEqual(len(messages),1)
            self.assertEqual(messages[0].header.frame_id,'odom_epoch')
            self.assertEqual(messages[0].header.stamp.sec,1)
            self.assertAlmostEqual(messages[0].twist.twist.linear.x,0.)
            self.assertAlmostEqual(messages[0].twist.twist.linear.y,-1.)
            self.assertEqual(msg.header.frame_id,'odom_epoch' if hardware else 'raw')
            self.assertEqual(messages[0] is msg,hardware)

if __name__=='__main__':unittest.main()
