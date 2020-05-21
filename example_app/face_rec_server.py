import cv2
import numpy as np
import os
import sys
import imagezmq
from twilio.rest import Client
import json
import argparse

# CLI options
argparser = argparse.ArgumentParser(description='Face Detection application with text notifications')
argparser.add_argument('-c', '--config', type=str,
			default='config',
			help='configuration file containing user ids (default is \'config\')')
args = argparser.parse_args()
config = args.config

if not os.path.isfile(config):
    print("Error: config file \'{}\' does not exist".format(config), file=sys.stderr)
    sys.exit(-1)

# get names associated with user ids
names = None
try:
    with open(config, 'r') as f:
        c = json.load(f)
        names = ["None"] + c["ids"]
except Exception as e:
    print(e)
    print("Error parsing config file", file=sys.stderr)
    sys.exit(-1)


# Twilio stuff
person_recognized = "RPi has detected {0}."
person_unrecognized = "RPi has detected a stranger."
# Your Account Sid and Auth Token from twilio.com/console
# Your recipient's phone number
# Make sure to run `source ./twilio.env` to set env vars
account_sid = os.environ['TWILIO_ACCOUNT_SID']
auth_token = os.environ['TWILIO_AUTH_TOKEN']
outgoing = os.environ['TWILIO_OUTGOING']
recipient = os.environ['TWILIO_RECIPIENT']
client = Client(account_sid, auth_token)

recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read('trainer/trainer.yml')
cascadePath = "haarcascade_frontalface_default.xml"
faceCascade = cv2.CascadeClassifier(cascadePath);

font = cv2.FONT_HERSHEY_SIMPLEX

#iniciate id counter
id = 0


# ImageHub object for video stream
imageHub = imagezmq.ImageHub()


name_notified = {}
name_detected = {}
for id in names:
    name_notified[id] = 0
    name_detected[id] = 0

while True:

    # Receive the image and the dimensions
    (minDims, img) = imageHub.recv_image()
    # Send ack
    imageHub.send_reply(b'OK')
    
    img = cv2.flip(img, 1) # Flip vertically
    gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

    faces = faceCascade.detectMultiScale(
        gray,
        scaleFactor = 1.2,
        minNeighbors = 5,
        minSize = (int(minDims[0]), int(minDims[1])),
       )

    for(x,y,w,h) in faces:

        cv2.rectangle(img, (x,y), (x+w,y+h), (0,255,0), 2)

        id, error = recognizer.predict(gray[y:y+h,x:x+w])
        
        if (error < 90):
            id = names[id]
            confidence = "  {0}%".format(round(100 - error))
            
            if round(100-error) > 25:
                name_detected[id] = 1
        else:
            id = "unknown"
            confidence = "  {0}%".format(round(100 - error))

            name_detected["None"] = 1

        #print("ID: ", id, " CONFIDENCE: ", confidence)

            
        for name, detected in name_detected.items():
            if detected == 1 and name_notified[name] == 0:
                if name == "None":
                    message = client.messages.create(
                         body=person_unrecognized,
                         from_=outgoing,
                         to=recipient
                     )
                else:
                    message = client.messages.create(
                             body=person_recognized.format(name),
                             from_=outgoing,
                             to=recipient
                         )
                name_notified[name] = 1
            name_detected[name] = 0

        
# Do a bit of cleanup
print("\n [INFO] Exiting Program and cleanup stuff")
cam.release()
cv2.destroyAllWindows()
