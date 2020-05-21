from imutils.video import VideoStream
import cv2
import imagezmq
import argparse
import socket
import time
import socket
import sys
import os
import json
import signal
import sys
import RPi.GPIO as GPIO

# Customize the below variables 
manager_ip = "172.0.0.2"
request_port = 60001
shutdown_port = 60002
image = "cdesiniotis/face_rec_server"
#-----------------------------


use_motion = int(input("Use motion detector?  Input 1 if yes, 0 if no: "))
use_motion = 0

if use_motion:
    # Motion sensor
    GPIO.setmode(GPIO.BOARD)    #numbering pins based on their actual order on the board, not their label
    GPIO.setup(11, GPIO.IN)

def create_connection(ip, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((ip, port))
    except (ConnectionRefusedError, OSError):
        print("[ERROR] Error connecting to manager", file=sys.stderr)
        sys.exit(-1)

    #print("\t[INFO] Successfully connected to {}\n".format(ip), file=sys.stderr)
    #print("\n[INFO] Successfully connected to the request server\n", file=sys.stderr)
    return s

def shutdown_application(manager_ip, shutdown_port, request):
    print("\n[INFO] Connecting to the shutdown server...\n")
    s = create_connection(manager_ip, shutdown_port)

    print("[INFO] Sending shutdown request...\n")
    s.sendall(json.dumps(request).encode())
    print("[INFO] Successfully sent: \n{}\n".format(json.dumps(request, indent=3)))
    resp = s.recv(1024)
    resp = json.loads(resp.decode())
    print("[INFO] RESPONSE: ", resp)
    s.close()

print("\n[INFO] Connecting to the request server...")
s = create_connection(manager_ip, request_port)
print("\n[INFO] Successfully connected to request server\n")

print("[INFO] Sending request...\n")
request = {"image":image,"application_port":5555,"protocol":"tcp"}
s.sendall(json.dumps(request).encode())
print("[INFO] Successfully sent: \n{}\n".format(json.dumps(request, indent=3)))
manager_resp = s.recv(1024)
manager_resp = json.loads(manager_resp.decode())
print("[INFO] Server response: \n{}\n".format(json.dumps(manager_resp, indent=3)))
s.close()

if manager_resp["resp-code"] != 0:
    print("[ERROR] Non-zero response code from server.")
    print("[ERROR] Server side failure message: ", manager_resp["failure-msg"])
    print("[ERROR] Exiting...")
    sys.exit(-1)

# Signal handler
# Makes sure to send a shutdown request when a signal is received
# i.e. shutdown app when killing the program
def handler(signal, frame):
    print("\n[INFO] Received signal ", signal)
    shutdown_application(manager_ip, shutdown_port, manager_resp)
    sys.exit(0)

# Register all catchable signals
catchable_sigs = set(signal.Signals) - {signal.SIGKILL, signal.SIGSTOP, signal.SIGWINCH}
for sig in catchable_sigs:
    signal.signal(sig, handler)

ip = manager_resp["ip"]
port = manager_resp["port"]
sender = imagezmq.ImageSender(connect_to="tcp://{}:{}".format(ip,port))

cam = cv2.VideoCapture(0)
cam.set(3, 640)
cam.set(4, 480)

minW = 0.1*cam.get(3)
minH = 0.1*cam.get(4)


print("[INFO] Connecting to application...\n")
try:
    _, frame = cam.read()
    resp = sender.send_image((minW, minH),frame)
    #print("[INFO] Server response: ", resp)
    print("[INFO] Successfully connected to application\n")
except Exception as e:
    print("\n[ERROR] e\n")
    shutdown_application(manager_ip, shutdown_port, manager_resp)
    sys.exit(-1)

if use_motion:
    while True:
        if GPIO.input(11) == 1:
            try:
                _, frame = cam.read()
                print("\n[INFO] Sending image\n")
                resp = sender.send_image((minW, minH),frame)
                #print("[INFO] Server response: ", resp)
            except Exception as e:
                print("\n[ERROR] e\n")
                shutdown_application(manager_ip, shutdown_port, manager_resp)
                sys.exit(-1)
else:
    count = 0
    print("[INFO] Beginning to stream video...\n")
    while (True):
        try:
            _, frame = cam.read()
            #print("\n[INFO] Sending image\n")
            resp = sender.send_image((minW, minH),frame)
            count += 1
            if count%5 == 0:
                print("[INFO] Successfully streamed {} frames\n".format(count))
            #print("[INFO] Server response: ", resp)
        except Exception as e:
            print("\n\t[ERROR] e\n")
            shutdown_application(manager_ip, shutdown_port, manager_resp)
            sys.exit(-1)
    duration = time.time() - start
