from setuptools import setup
setup(name='uav_localization', version='0.1.0', packages=['uav_localization'],
      data_files=[('share/ament_index/resource_index/packages', ['resource/uav_localization']), ('share/uav_localization',['package.xml'])],
      install_requires=['setuptools'], zip_safe=True,
      entry_points={'console_scripts':['localization_adapter=uav_localization.node:main']})
