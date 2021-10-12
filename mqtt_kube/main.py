import os
import sys
import logging

from functools import partial

import gevent
import gevent.monkey
gevent.monkey.patch_all()
gevent.get_hub().SYSTEM_ERROR = BaseException

import mqtt_kube.k8s.api
import mqtt_kube.binding
import mqtt_kube.config
import mqtt_kube.mqtt
import mqtt_kube.server

FORMAT = '%(asctime)-15s %(levelname)s [%(module)s] %(message)s'
logging.basicConfig(format=FORMAT, level=logging.DEBUG)

logging.getLogger('kubernetes.client.rest').setLevel(logging.INFO)

import urllib3
urllib3.disable_warnings()


def cli():
    config_file = 'config-dev.yaml' if len(sys.argv) < 2 else sys.argv[1]
    config = mqtt_kube.config.Config(config_file)

    mqtt = mqtt_kube.mqtt.Mqtt(**config.mqtt)

    kubeconfig = os.environ.get('KUBECONFIG', None)
    kube_client = mqtt_kube.k8s.api.get_client_api(kubeconfig)

    binding = mqtt_kube.binding.Binding(kube_client, mqtt, config.bindings)

    server = mqtt_kube.server.Server(**config.http)

    # mqtt.open()
    server.open()
    mqtt_loop = mqtt.run()
    binding.open()

    logging.info('Started')

    try:
        gevent.joinall((mqtt_loop,))
    except KeyboardInterrupt:
        server.close()
        mqtt.close()

