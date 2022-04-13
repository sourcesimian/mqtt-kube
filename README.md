MQTT Kube <!-- omit in toc -->
===

***Kubernetes API to MQTT connector service***

A service that maps MQTT topics to Kubernetes objects, configurable via YAML.

This capability presents many possible use cases. An example is to switch a media server on and off as though it were an appliance or launch a Job workload based on some demand.

- [Installation](#installation)
  - [Docker](#docker)
  - [Kubernetes](#kubernetes)
  - [MQTT Infrastructure](#mqtt-infrastructure)
- [Configuration](#configuration)
  - [MQTT](#mqtt)
    - [MQTT - Basic Auth](#mqtt---basic-auth)
    - [MQTT - mTLS Auth](#mqtt---mtls-auth)
  - [Web Server](#web-server)
  - [Logging](#logging)
  - [Bindings](#bindings)
    - [MQTT Associations](#mqtt-associations)
      - [Watch](#watch)
      - [Patch](#patch)
      - [Action](#action)
        - [Action Templates](#action-templates)
    - [Value Mapping](#value-mapping)
- [Contribution](#contribution)
  - [Development](#development)
- [License](#license)

# Installation
Prebuilt container images are available on [Docker Hub](https://hub.docker.com/r/sourcesimian/mqtt-kube).
## Docker
Run
```
docker run -n mqtt-kube -d -it --rm -p 8080:8080 \
    --volume my-config.yaml:/config.yaml:ro \
    --volume $HOME/.kube/config:/kubeconfig:ro \
    --env KUBECONFIG=/kubeconfig \
    sourcesimian/mqtt-kube:latest
```

## Kubernetes
When running **mqtt-kube** on the same Kubernetes cluster that you wish to interact with **mqtt-kube** can make use of [Service Accounts](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/). Typically this would be configured as:

```
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: iot-mqtt-kube
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
  - kind: ServiceAccount
    name: mqtt-kube
    namespace: iot
```

```
apiVersion: v1
kind: ServiceAccount
metadata:
  name: mqtt-kube
  namespace: iot
```

And a typical Deployment would look something like:
```
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mqtt-kube
  namespace: iot
spec:
  template:
    spec:
      serviceAccountName: mqtt-kube
      volumes:
      - name: config
        configMap:
          name: mqtt-kube-config
      containers:
      - name: mqtt-kube
        image: sourcesimian/mqtt-kube:latest
        command: ["/usr/local/bin/mqtt-kube"]
        args: ["/config/config.yaml"]
        volumeMounts:
        - name: config
          mountPath: /config
        livenessProbe:
          initialDelaySeconds: 30
          periodSeconds: 30
          httpGet:
            path: /api/health
            port: 8080
```

## MQTT Infrastructure
An installation of **mqtt-kube** will need a MQTT broker to connect to. There are many possibilities available. [Eclipse Mosquitto](https://github.com/eclipse/mosquitto/blob/master/README.md) is a great self hosted option with many ways of installation including pre-built containers on [Docker Hub](https://hub.docker.com/_/eclipse-mosquitto).

To compliment your MQTT infrastructure you may consider the following other microservices:
| Service | Description |
|---|---|
| [mqtt-panel](https://github.com/sourcesimian/mqtt-panel/blob/main/README.md) | A self hostable service that connects to a MQTT broker and serves a progressive web app panel. |
| [mqtt-ical](https://github.com/sourcesimian/mqtt-ical/blob/main/README.md) | Publishes values to MQTT topics based on events in an iCal Calendar. |
| [NodeRED](https://nodered.org/) | A flow-based visual programming tool for wiring together devices, with built in MQTT integration and many others available. Can easily be used to add higher level behaviours. |

# Configuration
**mqtt-kube** consumes a [YAML](https://yaml.org/) file. To start off you can copy [config-basic.yaml](./config-basic.yaml)

## MQTT
```
mqtt:
  host: <host>                  # optional: MQTT broker host, default: 127.0.0.1
  port: <port>                  # optional: MQTT broker port, default 1883
  client-id: mqtt-gpio          # MQTT client identifier, often brokers require this to be unique
  topic-prefix: <topic prefix>  # optional: Scopes the MQTT topic prefix
  auth:                         # optional: Defines the authentication used to connect to the MQTT broker
    type: <type>                # Auth type: none|basic|mtls, default: none
    ... (<type> specific options)
```

### MQTT - Basic Auth
```
    type: basic
    username: <string>          # MQTT broker username
    password: <string>          # MQTT broker password
```

### MQTT - mTLS Auth
```
    type: mtls
    cafile: <file>              # CA file used to verify the server
    certfile: <file>            # Certificate presented by this client
    keyfile: <file>             # Private key presented by this client
    keyfile_password: <string>  # optional: Password used to decrypt the `keyfile`
    protocols:
      - <string>                # optional: list of ALPN protocols to add to the SSL connection
```

## Web Server
```
http:
  bind: <bind>                  # optional: Interface on which web server will listen, default 0.0.0.0
  port: <port>                  # Port on which web server will listen, default 8080
  max-connections: <integer>    # optional: Limit the number of concurrent connections, default 100
```

The web server exposes the following API:
* `/api/health` - Responds with 200 if service is healthy

## Logging
```
logging:
  level: INFO                   # optional: Logging level, default DEBUG
```

## Bindings
A binding is a functional element which is used to connect a Kubernetes object to one or more MQTT topics and payloads.

Bindings are defined under the `bindings` key:
```
bindings:
- ...
```
All bindings have the following form:
```
  - namespace: <string>         # The Kubernetes namespace in which the object resides
    resource: <workload>        # The Kubernetes object type: Deployment|DaemonSet|Job
    name: <string>              # The name of the Kubernetes object
    (MQTT associations ...)
```

### MQTT Associations
Bindings are associated with MQTT topics by adding further sections:
#### Watch
A watch association allows you to define a `locus` within the object to watch. On change the value will be published to the `topic`.
```
    watch:
    - locus: <jsonpath>         # Value location in Kubernetes object
      topic: <topic>            # MQTT topic where payload is published
      qos: [0 | 1 | 2]          # optional: MQTT QoS to use, default: 1
      retain: [False | True]    # optional: Publish with MQTT retain flag, default: False
      values:                   # optional: Transform the value published to MQTT
        map:                    # Key to value mapping. Kubernetes to MQTT
          <key>: <value>
          ...
    ...
```
 [JSON Path](https://goessner.net/articles/JsonPath/) is a way of referencing locations within a JSON document.

 This example will watch the `availableReplicas` in our object. If the value is `1` then `ON` will be published to the topic, and if the value is `None` then `OFF` will be published to the topic.
 
 ```
    watch:
    - locus: "status.availableReplicas"
      topic: jellyfin/power/state
      qos: 1
      retain: true
      values:
        1: "ON"
        ~: "OFF"
 ```

In YAML the '`~`' character is used to represent `None`.

The values map can be extended to support transforms, regular expressions and lambda tests functions. See [Value Mapping](#value-mapping) for more detail.
 

#### Patch
A patch association allows you to listen on a MQTT topic for certain values and then patch a `locus` within the Kubernetes object.
```
    patch:
    - topic: <topic>            # MQTT topic where payload is published
      locus: <jsonpath>         # Value location in Kubernetes object
      values:                   # Mapping of MQTT payloads to object values
        map:                    
          <key>: <value>        # Key to value mapping: MATT to Kubernetes
          ...
    ...
```

This example will patch the `replicas` of the kubernetes object to `1` when `ON` is recieved on the topic, and to `0` when `OFF` is received on the topic.
```
    patch:
    - topic: jellyfin/power/set
      locus: "spec.replicas"
      values:
        map:
          "ON": 1
          "OFF": 0
```

#### Action
An action association allows you to listen on a MQTT topic for certain values and then launch or delete a Kubernetes object.
```
    action:
    - topic: <topic>            # MQTT topic where payload is published
      launch: <object YAML file>  # YAML template file describing the object
      values:                   # Mapping of MQTT payloads to actions
        map:
          "RUN": "launch"
          "STOP": "delete"
    ...
```

This example will create a Kubernetes Job when `RUN` is recieved on the topic, and delete the Job when `STOP` is received.
```
    action:
    - topic: webhook/cmd
      launch: !relpath job-foo.yaml
      values:
        map:
          "RUN": "launch"
          "STOP": "create"
```
##### Action Templates
The template file for the launch object should be in the usual Kubernetes YAML format. Values can be templated using [Mako template](https://docs.makotemplates.org/en/latest/syntax.html) syntax. The base keys included in the template context are:
| Key | Description |
|---|---|
| `binding` | The config tree for the binding |
| `action` | The config tree for the action |
| `uid` | A unique 8 character string that can be used to compose Kubernetes identifiers |
| `match` | The context from the value matching process. If JSONPath was used there will be a `.json` sub-key containing the full blob from the pauyload. If a regular expression was used with named groups they will be present as sub keys. The original input value as `.input` |

### Value Mapping
Value mapping is applicable to all MQTT associations. In each case there is a direction. Watches map from a value within a Kubernetes object to a MQTT payload. Patches and Actions map from a MQTT payload to a value or action in Kubernetes.

```
      values:
        transform: <python code>  # Modify the inbound value
        jsonpath: <jsonpath>      # Select a a value from a Json blob
        map:
          <input>: <output>       # Translate the value to its final form
          ...
```

The values map `<input>` expressions can take on the following forms:
| Form | Description |
|---|---|
| Literal Value | An input expression can simply be a literal string, integer of float that is matched with the source value. Or be used as the output value. |
| Regular Expressions | When the input expression is prefixed with `re:` then the remainder of the string is used as a regular expression match. If groups are specified they will be available by name in the [Format String](#format-string) context. |
| Lambda Expression | When the input expression is prefixed with `lambda ` then this will be used as a unary match function. |
| Format String | When the output expression contains Python [f-string](https://docs.python.org/3/reference/lexical_analysis.html#f-strings) replacement fields it will be rendered using the context from the matching process. |

# Contribution
Yes sure! And please. I built **mqtt-kube** as a building block in my MQTT centric home automation. I want it to be a project that is quick and easy to use and makes DIY home automation more fun and interesting.

Before pushing a PR please ensure that `make check` and `make test` are clean and please consider adding unit tests.

## Development
Setup the virtualenv:

```
python3 -m venv virtualenv
. ./virtualenv/bin/activate
python3 ./setup.py develop
```

Run the service:
```
export KUBECONFIG=$HOME/.kube/config
mqtt-kube ./config-demo.yaml
```

# License

In the spirit of the Hackers of the [Tech Model Railroad Club](https://en.wikipedia.org/wiki/Tech_Model_Railroad_Club) from the [Massachusetts Institute of Technology](https://en.wikipedia.org/wiki/Massachusetts_Institute_of_Technology), who gave us all so very much to play with. The license is [MIT](LICENSE).
