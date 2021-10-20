MQTT Kube <!-- omit in toc -->
===

***Kubernetes API to MQTT connector service***

A service that maps Kubernetes object values to and from topics on MQTT, configurable via YAML.

This capability presents many possible use cases. An example is to switch a media server on and off as though it were an appliance, by mapping the `spec.replicas` value of the deployment onto a MQTT topic.


# Containerization
Example `Dockerfile`:

```
FROM python:3.9-slim

COPY mqtt-kube/python3-requirements.txt /
RUN pip3 install -r python3-requirements.txt

COPY mqtt-kube/setup.py /
COPY mqtt-kube/mqtt_kube /mqtt_kube
RUN python3 /setup.py develop

COPY my-config.yaml /config.yaml

ENTRYPOINT ["/usr/local/bin/mqtt-kube", "/config.yaml"]
```

# Development
Setup the virtualenv:

```
python3 -m venv virtualenv
. ./virtualenv/bin/activate
python3 ./setup.py develop
```

Run the server:

```
mqtt-kube ./config-demo.yaml
```

# License

In the spirit of the Hackers of the [Tech Model Railroad Club](https://en.wikipedia.org/wiki/Tech_Model_Railroad_Club) from the [Massachusetts Institute of Technology](https://en.wikipedia.org/wiki/Massachusetts_Institute_of_Technology), who gave us all so very much to play with. The license is [MIT](LICENSE).
