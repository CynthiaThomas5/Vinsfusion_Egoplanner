from glob import glob
from setuptools import setup

setup(
    name='uav_navigation',
    version='0.1.0',
    packages=['uav_navigation'],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/uav_navigation']),
        ('share/uav_navigation', ['package.xml']),
        ('share/uav_navigation/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    entry_points={
        'console_scripts': [
            'navigation_supervisor=uav_navigation.node:main',
        ],
    },
)
