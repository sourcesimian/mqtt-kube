from setuptools import setup


setup(
    name="mqtt-kube",
    version=open('version', 'rt', encoding="utf8").read().strip(),
    description="Kubernetes API to MQTT connector service",
    author="Source Simian",
    url="https://github.com/sourcesimian/mqtt-panel",
    license="MIT",
    packages=['mqtt_kube'],
    install_requires=open('python3-requirements.txt', encoding="utf8").readlines(),
    entry_points={
        "console_scripts": [
            "mqtt-kube=mqtt_kube.main:cli",
        ]
    },
)
