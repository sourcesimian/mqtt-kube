import importlib.metadata
import logging
import os
import sys

import gevent
import gevent.monkey
gevent.monkey.patch_all()
gevent.get_hub().SYSTEM_ERROR = BaseException

import urllib3                      # noqa: E402 pylint: disable=C0413

import mqtt_kube.binding.binding    # noqa: E402 pylint: disable=C0413
import mqtt_kube.config             # noqa: E402 pylint: disable=C0413
import mqtt_kube.k8s.api            # noqa: E402 pylint: disable=C0413
import mqtt_kube.mqtt               # noqa: E402 pylint: disable=C0413
import mqtt_kube.mqttjson           # noqa: E402 pylint: disable=C0413
import mqtt_kube.server             # noqa: E402 pylint: disable=C0413

FORMAT = '%(asctime)s.%(msecs)03d %(levelname)s [%(module)s] %(message)s'
logging.basicConfig(format=FORMAT, level=logging.DEBUG, datefmt='%Y-%m-%dT%H:%M:%S')

logging.getLogger('kubernetes.client.rest').setLevel(logging.INFO)

urllib3.disable_warnings()


def cli():
    meta = dict(importlib.metadata.metadata('mqtt_kube'))
    logging.info('Running mqtt-kube v%s', meta['Version'])

    config_file = 'config-dev.yaml' if len(sys.argv) < 2 else sys.argv[1]
    config = mqtt_kube.config.Config(config_file)

    logging.getLogger().setLevel(level=config.log_level)

    mqtt = mqtt_kube.mqtt.Mqtt(config.mqtt)

    kubeconfig = os.environ.get('KUBECONFIG', None)
    kube_client = mqtt_kube.k8s.api.get_client_api(kubeconfig)
    if kube_client is None:
        return 1

    binding = mqtt_kube.binding.binding.Binding(kube_client, mqtt, config.bindings)

    server = mqtt_kube.server.Server(**config.http)

    try:
        # mqtt.open()
        server.open()
        mqtt_loop = mqtt.run()
        binding.open()

        logging.info('Started')
        gevent.joinall((mqtt_loop,))
    except KeyboardInterrupt:
        server.close()
        mqtt.close()

    return 0
