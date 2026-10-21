from setuptools import setup
setup(name='uav_mapping', version='0.1.0', packages=['uav_mapping'],
      data_files=[('share/ament_index/resource_index/packages', ['resource/uav_mapping']), ('share/uav_mapping',['package.xml'])],
      install_requires=['setuptools'], zip_safe=True,
      entry_points={'console_scripts':[
          'depth_health_monitor=uav_mapping.node:main',
          'mapping_input_adapter=uav_mapping.adapter:main']})
