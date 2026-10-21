from glob import glob
from setuptools import setup

setup(
    name='uav_px4_bridge',
    version='0.1.0',
    packages=['uav_px4_bridge'],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/uav_px4_bridge']),
        ('share/uav_px4_bridge', ['package.xml']),
        ('share/uav_px4_bridge/launch', glob('launch/*.py')),
    ],
    install_requires=['setuptools'],
    entry_points={'console_scripts': [
        'px4_bridge = uav_px4_bridge.px4_bridge_node:main',
    ]},
    zip_safe=True,
)
