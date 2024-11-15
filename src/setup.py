from setuptools import setup

setup(
    name="network-monitor",
    version="1.0",
    description="Network Monitoring Tool",
    author="Jacques Artgraven",
    packages=[""],
    install_requires=[
        'speedtest-cli',
        'ping3',
        'ttkthemes'
    ],
)