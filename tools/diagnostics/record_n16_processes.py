#!/usr/bin/env python3
"""Read-only process identity and source-clock recorder; never controls flight."""
import argparse,hashlib,json,os,time
from pathlib import Path
import rclpy
from rosgraph_msgs.msg import Clock
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
ROLES=('px4','vins_node','ego_planner_node','traj_server','navigation_supervisor','px4_bridge',
       'mapping_input_adapter','localization_adapter','parameter_bridge','MicroXRCEAgent','gazebo_server')


def process_roles():
    found={k:[] for k in ROLES}
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            args=[x.decode(errors='replace') for x in (p/'cmdline').read_bytes().split(b'\0') if x]
            if not args:continue
            executable=Path(args[0]).name
            script=Path(args[1]).name if len(args)>1 and 'python' in executable else ''
            stat=(p/'stat').read_text();state_and_fields=stat.rsplit(')',1)[1].split()
            if state_and_fields[0]=='Z':continue
            key=f'{p.name}:{state_and_fields[19]}'  # PID plus kernel starttime, not PID alone.
            for role in ROLES:
                if role in (executable,script):found[role].append(key)
            if 'gz sim -s' in ' '.join(args) and '--headless-rendering' in ' '.join(args):found['gazebo_server'].append(key)
        except (OSError,IndexError):continue
    return found


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('--max-wall-s',type=float,default=7200);a=p.parse_args()
    rclpy.init();node=Node('n16_readonly_process_observer');clock={'ns':None}
    node.create_subscription(Clock,'/clock',lambda m:clock.update(ns=m.clock.sec*10**9+m.clock.nanosec),qos_profile_sensor_data)
    path=a.run/'n16-process-observation.jsonl';rows=[];start=time.monotonic();last=-1;complete=False
    if path.exists():raise RuntimeError('refuse existing process evidence')
    with path.open('w') as stream:
        while rclpy.ok() and time.monotonic()-start<a.max_wall_s:
            rclpy.spin_once(node,timeout_sec=.1);elapsed=time.monotonic()-start
            if elapsed-last>=1:
                row={'wall_elapsed_s':elapsed,'sim_ns':clock['ns'],'roles':process_roles()};rows.append(row)
                stream.write(json.dumps(row)+'\n');stream.flush();last=elapsed
            try:
                safe=json.loads((a.run/'safe-to-stop.json').read_text())
                if safe.get('safe_to_stop_project_container') is True:complete=True;break
            except (OSError,ValueError):pass
    report={'schema':'n16-process-observation/v1','run_id':a.run.name,
            'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'expected_roles':list(ROLES),'sample_count':len(rows),
            'rows_file':path.name,'rows_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'safe_terminal_observed':complete,'may_publish_control':False,'observer_pid':os.getpid()}
    (a.run/'n16-process-observation.json').write_text(json.dumps(report,indent=2)+'\n');node.destroy_node();rclpy.shutdown()

if __name__=='__main__':main()
