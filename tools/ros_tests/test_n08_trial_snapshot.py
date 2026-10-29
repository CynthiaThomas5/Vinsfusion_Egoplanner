"""Production snapshot admission tests; source ROS and install before running."""
import sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import run_n08_braking_trial as trial

class SnapshotTests(unittest.TestCase):
 def response(self,accepted=True,reason='ok',epoch='e'):
  return NS(accepted=accepted,reason=reason,epoch=epoch,map_id='m',
   header=NS(frame_id='odom_'+epoch),
   last_depth_source_stamp=NS(sec=1,nanosec=0),last_fusion_stamp=NS(sec=1,nanosec=0),
   size_x=1,size_y=1,size_z=1,occupancy_data=[0],origin=NS(x=0.,y=0.,z=0.),resolution=.15)
 def capture(self,responses,status_change=False):
  now=[10.];index=[0]
  node=NS(map_status=NS(epoch='e',map_id='m',input_ready=True,reset_acknowledged=True),map_status_wall=10.,clock_ns=1100000000)
  def call(_):
   r=responses[min(index[0],len(responses)-1)];index[0]+=1
   return NS(done=lambda:True,result=lambda:r)
  node.snapshot_client=NS(wait_for_service=lambda **_:True,call_async=call)
  def spin(*_,**__):
   now[0]+=.1;node.map_status_wall=now[0]
   if status_change:node.map_status.map_id='changed'
  with tempfile.TemporaryDirectory() as folder:
   with patch.object(trial.time,'monotonic',side_effect=lambda:now[0]),patch.object(trial,'spin_until',return_value=True),patch.object(trial.rclpy,'spin_once',side_effect=spin):
    raw,meta=trial.capture_snapshot(node,Path(folder),'capture','e','m')
   rows=__import__('json').loads((Path(folder)/'capture-requests.json').read_text())
   return raw,meta,rows
 def test_transient_pending_fusion_retries_then_uses_accepted_grid(self):
  raw,meta,rows=self.capture([self.response(False,'no_fresh_fused_depth'),self.response()])
  self.assertEqual(len(rows),2);self.assertFalse(rows[0]['accepted']);self.assertEqual(meta['source_age_s'],.1);self.assertEqual(raw['occupancy'].shape,(1,1,1))
 def test_epoch_mismatch_never_retried(self):
  with self.assertRaisesRegex(RuntimeError,'wrong_identity'):self.capture([self.response(epoch='wrong')])
 def test_depth_gate_failure_never_retried(self):
  with self.assertRaisesRegex(RuntimeError,'depth_pose_gate_closed'):self.capture([self.response(False,'depth_pose_gate_closed'),self.response()])
 def test_persistent_transient_refusal_has_fixed_deadline(self):
  with self.assertRaisesRegex(RuntimeError,'transient_deadline'):self.capture([self.response(False,'no_fresh_fused_depth')])
 def test_changed_map_during_wait_refuses(self):
  with self.assertRaisesRegex(RuntimeError,'map_identity_changed'):self.capture([self.response(False,'no_fresh_fused_depth'),self.response()],True)
 def test_service_wait_must_be_followed_by_fresh_map_status(self):
  now=[10.]; node=NS(map_status=NS(epoch='e',map_id='m',input_ready=True,
   reset_acknowledged=True,reason='ready'),map_status_wall=10.,clock_ns=1100000000)
  response=self.response()
  def wait_for_service(**_):
   now[0]+=1.0  # Executor callbacks are queued while service discovery blocks.
   return True
  node.snapshot_client=NS(wait_for_service=wait_for_service,
   call_async=lambda _:NS(done=lambda:True,result=lambda:response))
  def refresh_after_wait(n,predicate,timeout):
   now[0]+=.1
   n.map_status_wall=now[0]  # Process the queued MapStatus callback.
   return predicate()
  with tempfile.TemporaryDirectory() as folder:
   with patch.object(trial.time,'monotonic',side_effect=lambda:now[0]),\
        patch.object(trial,'spin_until',side_effect=refresh_after_wait):
    _,meta=trial.capture_snapshot(node,Path(folder),'capture','e','m')
  self.assertAlmostEqual(meta['source_age_s'],.1)
 def test_map_identity_change_during_service_wait_refuses_before_snapshot(self):
  now=[10.]; node=NS(map_status=NS(epoch='e',map_id='m',input_ready=True,
   reset_acknowledged=True,reason='ready'),map_status_wall=10.,clock_ns=1100000000)
  calls=[]
  def wait_for_service(**_):
   now[0]+=1.0
   node.map_status.map_id='replacement'
   return True
  node.snapshot_client=NS(wait_for_service=wait_for_service,
   call_async=lambda _:calls.append('called'))
  def refresh_after_wait(n,predicate,timeout):
   now[0]+=.1;n.map_status_wall=now[0];return predicate()
  with tempfile.TemporaryDirectory() as folder:
   with patch.object(trial.time,'monotonic',side_effect=lambda:now[0]),\
        patch.object(trial,'spin_until',side_effect=refresh_after_wait):
    with self.assertRaisesRegex(RuntimeError,'map_identity_changed_after_snapshot_service_wait'):
     trial.capture_snapshot(node,Path(folder),'capture','e','m')
  self.assertEqual(calls,[])
 def test_accepted_but_stale_snapshot_still_refuses(self):
  r=self.response();r.last_depth_source_stamp.sec=0
  with self.assertRaisesRegex(RuntimeError,'source_or_fusion_stale'):self.capture([r])
if __name__=='__main__':unittest.main()
