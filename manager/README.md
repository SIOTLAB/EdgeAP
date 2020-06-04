# EdgeAP Management Server

## Overview

The management server is responsible for overseeing applications running on wireless access points.
More specifically, it must receive & process application requests, start-up the application on the appropriate access point, and manage the life cycle of the application.

## Secure Docker Daemon Socket

The management server must have access to dockerd running on the access point.

See [this link](https://success.docker.com/article/how-do-i-enable-the-remote-api-for-dockerd) for enabling the remote API for dockerd on the access point.

To secure the docker daemon socket, by enabling TLS and creating CA, server and client keys with OpenSSL, see [this link](https://docs.docker.com/engine/security/https/).

To automate the process of key creation, see [this link](https://gist.github.com/kekru/974e40bb1cd4b947a53cca5ba4b0bbe5).

## Configuration

The configuration file is used to specify the remote access points the management server is responsible for. Each entry in `remotes` corresponds to one access point, and must contain information about the access point and contain the appropriate keys.

An example configuration file:
```
{
	"manager_ip": "172.0.0.1",
	"remotes":
		{
			"10.0.0.1":
				{
					"port": "2376",
					"tlsverify": true,
					"certs_path": "/certs",
					"tlscacert": "ca.pem",
					"tlscert": "client-cert.pem",
					"tlskey": "client-key.pem"
				}
		}
}
```

## Prerequisites

`pip3 install -r requirements.txt`

## Run

`python3 edgeap.py`
