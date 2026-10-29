"""Read-only pre-goal context; missing data affects offline evidence, never flight."""
from pathlib import Path
import sys,json,time,hashlib
import rclpy
from rclpy.node import Node
from uav_interfaces.msg import MapStatus,NavigationCommand
from rosidl_runtime_py.convert import message_to_ordereddict
run,case,protocol=Path(sys.argv[1]),sys.argv[2],Path(sys.argv[3]);rclpy.init();n=Node('n17_readonly_scene_context');seen={'goal':False,'status':None}
n.create_subscription(MapStatus,'/mapping/status',lambda m:seen.update(status=m),10)
n.create_subscription(NavigationCommand,'/navigation/ego_goal',lambda m:seen.update(goal=True),10)
start=time.monotonic()
while rclpy.ok() and time.monotonic()-start<45:
 rclpy.spin_once(n,timeout_sec=.05);m=seen['status']
 if m is None or not m.epoch or not m.map_id:continue
 runtime=json.loads((run/'runtime-contract.json').read_text());record={'schema':'n17-scene-launch-record/v1','scene':case,'protocol_sha256':hashlib.sha256(protocol.read_bytes()).hexdigest(),'runtime_contract_sha256':runtime['sha256'],'map_id':m.map_id,'epoch':m.epoch,'map_status_stamp_ns':m.header.stamp.sec*10**9+m.header.stamp.nanosec,'pre_goal_record':not seen['goal'],'world_mutation_commands':[],'map_status':message_to_ordereddict(m),'context_recorder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 for name in ['n17-launch-record.json','n11-launch-record.json']:(run/name).write_text(json.dumps(record,indent=2)+'\n')
 (run/'n10-live-obstacle-observation.json').write_text(json.dumps({'schema':'n17-static-identity-context/v1','run_id':run.name,'runtime_contract_baseline_sha256':runtime['sha256'],'map_id_at_goal':m.map_id,'epoch':m.epoch,'world_mutation_commands':[],'source':'real MapStatus read before goal; no obstacle event or world-map input'},indent=2)+'\n');break
else:(run/'n17-context-insufficient.json').write_text(json.dumps({'reason':'MapStatus identity not observed; no flight-control effect'})+'\n')
n.destroy_node();rclpy.shutdown()
