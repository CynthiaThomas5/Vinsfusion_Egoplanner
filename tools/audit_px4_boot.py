"""Read-only native PX4 boot audit; no ROS participant or control command."""
import json,subprocess,re,hashlib
from pathlib import Path
import sys
run=Path(sys.argv[1]).resolve();build=run/'px4_sitl_default';names=['MPC_Z_V_AUTO_DN','MPC_LAND_SPEED','MPC_Z_VEL_MAX_DN','MPC_Z_VEL_MAX_UP','LNDMC_Z_VEL_MAX','MPC_Z_VEL_ALL','MPC_ACC_HOR','MPC_ACC_HOR_MAX','MPC_JERK_AUTO','MPC_XY_VEL_MAX','EKF2_EV_CTRL','EKF2_GPS_CTRL','UXRCE_DDS_SYNCT','SIM_GZ_EN_ODOM'];values={};outputs={}
for name in names:
 p=subprocess.run([str(build/'bin/px4-param'),'show',name],text=True,capture_output=True,check=True);outputs[name]=p.stdout
 match=re.search(r'\]\s*:\s*(-?[0-9.]+)',p.stdout);assert match,name+' missing';values[name]=float(match.group(1))
for name in ['parameters.bson','parameters_backup.bson','dataman','eeprom']:assert not (build/name).is_symlink(),'historical mutable state linked: '+name
assert values['MPC_Z_V_AUTO_DN']>=1.1*values['LNDMC_Z_VEL_MAX']
assert values['MPC_LAND_SPEED']>=1.1*values['LNDMC_Z_VEL_MAX']
assert values['MPC_Z_VEL_MAX_DN']>=1.1*values['LNDMC_Z_VEL_MAX']
expected=json.loads(Path('/workspace/config/components/px4_bridge/flight_limits.json').read_text())['parameters']['MPC_Z_VEL_MAX_UP']
assert abs(values['MPC_Z_VEL_MAX_UP']-expected)<1e-6 and values['MPC_Z_VEL_ALL']<0
assert values['EKF2_EV_CTRL']==15 and all(values[k]==0 for k in ['EKF2_GPS_CTRL','UXRCE_DDS_SYNCT','SIM_GZ_EN_ODOM'])
(run/'px4-boot-parameters.json').write_text(json.dumps({'scope':__doc__,'passed':True,'fresh_run_mutable_state_files':True,'parameters':values,'native_outputs':outputs},indent=2)+'\n')
