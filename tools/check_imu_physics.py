from pathlib import Path
import sys
import xml.etree.ElementTree as E
import math,json
run=Path(sys.argv[1]).resolve()
rate=float(E.parse('/workspace/simulation/models/d435i/model.sdf').findtext("model/link/sensor[@name='imu']/update_rate"))
step=float(E.parse(run/'vio_initialization.sdf').findtext('world/physics/max_step_size'))
assert math.isclose(rate*step,1,abs_tol=1e-12), 'IMU must sample every flight physics tick'
(run/'imu-physics-contract.json').write_text(json.dumps({'imu_hz':rate,'physics_step_s':step,'rate_times_step':rate*step})+'\n')
