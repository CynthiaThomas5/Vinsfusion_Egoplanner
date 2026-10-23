"""Offline truth path and sampled nominal envelope check; never publishes."""
import json,math,sys,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[2];run=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent
sys.path.insert(0,str(root/'tools'))
from evaluate_vins_motion import rotation
from audit_vehicle_envelope import audit
sys.path.insert(0,str(root/'src/own/uav_sim'))
from uav_sim.geometry import px4_sensor_mount
mount=px4_sensor_mount(root/'simulation/models/x500_d435i/model.sdf')
lever=np.array(mount['translation_frd_m'])*np.array([1,-1,-1])

sys.path.insert(0,str(Path(__file__).resolve().parent))
from world_geometry import transform, signed_box, signed_cylinder

assert np.allclose(signed_box(np.array([[0,0,0],[2,0,0],[2,2,0]]),np.ones(3)),[-1,1,math.sqrt(2)])
assert np.allclose(signed_cylinder(np.array([[0,0,0],[2,0,0],[2,0,2]]),1,1),[-1,1,math.sqrt(2)])
truth=json.loads((run/'debug-truth-evaluation.json').read_text())['samples'];flight=json.loads((run/'flight.json').read_text());positions=np.asarray([p['xyz'] for p in truth]);times=np.asarray([p['stamp_ns'] for p in truth]);assert (np.diff(times)>0).all()
# Gazebo OdometryPublisher takes worldPose(model), not the child-frame label.
# No xyz_offset is configured; convert model origin to the SDF camera IMU.
imu=np.asarray([p+rotation(t['q_xyzw'])@lever for p,t in zip(positions,truth)])
air=positions[:,2]>.5;assert air.any();minimum=np.full(len(positions),np.inf);nearest=np.full(len(positions),'',dtype=object);shapes=[]
world=ET.parse(root/'simulation/worlds/ego.sdf').getroot().find('world')
for model in world.findall('model'):
 for link in model.findall('link'):
  for collision in link.findall('collision'):
   g=collision.find('geometry');T=transform(model.findtext('pose'))@transform(link.findtext('pose'))@transform(collision.findtext('pose'));local=(imu-T[:3,3])@T[:3,:3];name=model.get('name')+'/'+link.get('name')
   if g.find('plane') is not None:continue
   if g.find('box') is not None:
    half=np.array(list(map(float,g.findtext('box/size').split())))/2;dist=signed_box(local,half);shapes.append(('box',T,half))
   elif g.find('cylinder') is not None:
    r=float(g.findtext('cylinder/radius'));h=float(g.findtext('cylinder/length'))/2;dist=signed_cylinder(local,r,h);shapes.append(('cylinder',T,r))
   else:raise ValueError('Unsupported collision geometry')
   better=dist<minimum;minimum[better]=dist[better];nearest[better]=name
radius=audit()['max_orientation_invariant_radius_all_rotor_angles_m'];k=np.flatnonzero(air)[int(np.argmin(minimum[air]))];xygoal=np.array([8.,0.]);errors=np.linalg.norm(positions[:,:2]-xygoal,axis=1);j=np.flatnonzero(air)[int(np.argmin(errors[air]))]
report={'scope':'Single-run offline Gazebo model-world truth plus sampled nominal body-envelope diagnostic; no control/truth feedback, no formal collision or acceptance qualification.','truth_frame_note':'OdometryPublisher model world pose with no xyz_offset; robot_base_frame text is a label only. IMU point reconstructed from the project SDF mount.','truth_source_reference':'https://raw.githubusercontent.com/gazebosim/gz-sim/gz-sim8/src/systems/odometry_publisher/OdometryPublisher.cc','sample_count':len(truth),'airborne_samples':int(air.sum()),'truth_x_range_m':[float(positions[:,0].min()),float(positions[:,0].max())],'closest_nominal_world_goal_xy_error_m':float(errors[j]),'closest_nominal_world_goal_xyz':positions[j].tolist(),'max_truth_sample_gap_sim_s':float(np.diff(times).max()/1e9),'nominal_imu_envelope_radius_m':radius,'minimum_airborne_imu_point_to_non_ground_obstacle_m':float(minimum[k]),'sampled_envelope_margin_m':float(minimum[k]-radius),'nearest_obstacle':str(nearest[k]),'at_world_model_xyz':positions[k].tolist(),'action_result':flight.get('action_result'),'landed_and_disarmed':flight.get('landed_and_disarmed'),'limitations':['Single sampled run, no continuous collision sweep proof.','Ground omitted from obstacle-distance diagnostic; takeoff/landing require intentional ground contact.','No multi-scene, braking-distance or uncertainty acceptance.']}
(run/'crossing-evaluation.json').write_text(json.dumps(report,indent=2)+'\n')
if '--plot' in sys.argv[2:]:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon,Circle
    fig,ax=plt.subplots(figsize=(9,8))
    for kind,T,size in shapes:
     if kind=='cylinder':ax.add_patch(Circle(T[:2,3],size,color='0.65'))
     else:
      h=size;corners=np.array([[-h[0],-h[1],0],[h[0],-h[1],0],[h[0],h[1],0],[-h[0],h[1],0]]);corners=(corners@T[:3,:3].T+T[:3,3])[:,:2];ax.add_patch(Polygon(corners,color='0.45'))
    ax.plot(positions[:,0],positions[:,1],color='#157ca8',lw=2,label='Gazebo actual trajectory');ax.scatter([-8,8],[0,0],c=['green','red'],s=60,zorder=5);ax.text(-8,-.6,'Start');ax.text(8,-.6,'Target');ax.set(xlim=(-10.5,10.5),ylim=(-10.5,10.5),xlabel='World X (m)',ylabel='World Y (m)',title='Room crossing: actual simulated trajectory');ax.set_aspect('equal');ax.grid(alpha=.2);ax.legend();fig.tight_layout();fig.savefig(run/'crossing-trajectory.png',dpi=150);plt.close(fig)
print(report)
