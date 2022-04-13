import logging
import os

import kubernetes
import kubernetes.config
import kubernetes.client


def get_client_api(kubeconfig=None):
    config = kubernetes.client.Configuration()

    if kubeconfig:
        kubernetes.config.load_kube_config(kubeconfig, client_configuration=config)
    else:
        try:
            kubernetes.config.load_incluster_config(client_configuration=config)
        except Exception as ex:  # pylint: disable=W0703
            logging.error('Unable to load Kubernetes API configuration, %s "%s"', ex.__class__.__name__, ex)
            return None

    config.verify_ssl = False
    # config.ssl_ca_cert = ...
    config.proxy = os.environ.get('https_proxy', None)

    api_client = kubernetes.client.ApiClient(configuration=config)
    return api_client
