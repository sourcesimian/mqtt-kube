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
        kubernetes.config.load_incluster_config(client_configuration=config)

    config.verify_ssl = False
    # config.ssl_ca_cert = ...
    config.proxy = os.environ.get('https_proxy', None)

    api_client = kubernetes.client.ApiClient(configuration=config)
    return api_client
