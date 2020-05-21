import socket
import sys
import os
import json
import time

manager_ip = "172.0.0.2"
request_port = 60001
shutdown_port = 60002

def create_connection(ip, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((ip, port))
    except (ConnectionRefusedError, OSError):
        print("Error connecting to manager", file=sys.stderr)
        sys.exit(-1)

    print("Successfully connected to {}".format(ip), file=sys.stderr)
    return s

print("Connecting to the request server...")
s = create_connection(manager_ip, request_port)

print("Sending request...")
request = {"image":"ubuntu","application_port":1234,"protocol":"tcp"}
s.sendall(json.dumps(request).encode())
print("Successfully sent: \n{}".format(json.dumps(request, indent=3)))
resp = s.recv(1024)
resp = json.loads(resp.decode())
print("RESPONSE: ", resp)
s.close()

print("Sleeping...")
time.sleep(5)

print("Connecting to the shutdown server...")
s = create_connection(manager_ip, shutdown_port)

print("Sending shutdown request...")
request = resp
s.sendall(json.dumps(request).encode())
print("Successfully sent: \n{}".format(json.dumps(request, indent=3)))
resp = s.recv(1024)
resp = json.loads(resp.decode())
print("RESPONSE: ", resp)
s.close()












    
