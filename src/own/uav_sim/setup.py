from setuptools import setup
from glob import glob
setup(name='uav_sim', version='0.1.0', packages=['uav_sim'],
      data_files=[('share/ament_index/resource_index/packages', ['resource/uav_sim']),
                  ('share/uav_sim', ['package.xml']), ('share/uav_sim/launch', glob('launch/*.py')),
                  ('share/uav_sim/models/x500_d435i',
                   ['../../../simulation/models/x500_d435i/model.sdf'])],
      entry_points={'console_scripts': ['debug_truth_adapter = uav_sim.debug_truth_adapter:main']},
      install_requires=['setuptools'], zip_safe=True)
