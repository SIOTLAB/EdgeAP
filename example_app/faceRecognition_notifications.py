import cv2
import numpy as np
import os
import sys
from twilio.rest import Client
import RPi.GPIO as GPIO
import time
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

    
#motion sensor stuff
#FOR EASY HELP: run command "pinout"
GPIO.setmode(GPIO.BOARD)    #numbering pins based on their actual order on the board, not their label
GPIO.setup(11, GPIO.IN)

#Twilio stuff
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

# Face classifier
recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read('trainer/trainer.yml')
cascadePath = "haarcascade_frontalface_default.xml"
faceCascade = cv2.CascadeClassifier(cascadePath);

font = cv2.FONT_HERSHEY_SIMPLEX

#iniciate id counter
id = 0

# names related to ids: example ==> Marcelo: id=1,  etc
#ames = ['None', "Cyrus","Philip","Jake","Michael","Chris","Justin"]

# Initialize and start realtime video capture
cam = cv2.VideoCapture(0)
cam.set(3, 640) # set video widht
cam.set(4, 480) # set video height

# Define min window size to be recognized as a face
minW = 0.1*cam.get(3)
minH = 0.1*cam.get(4)

print("Everything set up and ready to go")

name_notified = {}
name_detected = {}
for id in names:
    name_notified[id] = 0
    name_detected[id] = 0

use_motion = input("Use motion detector?  Input 1 if yes, 0 if no: ")

if use_motion == '1':
    while True:
        motion = GPIO.input(11)
        
        if motion==0:
            print("No motion detected")
        else:
            print("Motion detected")
            for i in range(0,50):   #keep from going indefinitely (needs to trigger according to motion)
                print("i: " + str(i))
                
                ret, img =cam.read()
                img = cv2.flip(img, 1) # Flip vertically

                gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

                faces = faceCascade.detectMultiScale(
                    gray,
                    scaleFactor = 1.2,
                    minNeighbors = 5,
                    minSize = (int(minW), int(minH)),
                   )

                for(x,y,w,h) in faces:
                    #print("x: {}\ty: {}\tw: {}\th: {}".format(x, y, w, h))

                    cv2.rectangle(img, (x,y), (x+w,y+h), (0,255,0), 2)

                    id, confidence = recognizer.predict(gray[y:y+h,x:x+w])

                    # Check if confidence is less them 100 ==> "0" is perfect match
                    if (confidence < 100):
                        id = names[id]
                        confidence_val = confidence
                        confidence = "  {0}%".format(round(100 -confidence))
                        
                        if round(100-confidence_val) > 25:
                            name_detected[id] = 1
                        
                    else:
                        id = "unknown"
                        confidence = "  {0}%".format(round(100 -confidence))
                        
                        name_detected["None"] = 1

                    cv2.putText(img, str(id), (x+5,y-5), font, 1, (255,255,255), 2)
                    cv2.putText(img, str(confidence), (x+5,y+h-5), font, 1, (255,255,0), 1)

                cv2.imshow('camera',img)

                k = cv2.waitKey(10) & 0xff # Press 'ESC' for exiting video
                if k == 27:
                    break
        
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
else:
    while True:
        ret, img =cam.read()
        img = cv2.flip(img, 1) # Flip vertically

        gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

        faces = faceCascade.detectMultiScale(
            gray,
            scaleFactor = 1.2,
            minNeighbors = 5,
            minSize = (int(minW), int(minH)),
           )

        for(x,y,w,h) in faces:
            #print("x: {}\ty: {}\tw: {}\th: {}".format(x, y, w, h))

            cv2.rectangle(img, (x,y), (x+w,y+h), (0,255,0), 2)

            id, confidence = recognizer.predict(gray[y:y+h,x:x+w])

            # Check if confidence is less them 100 ==> "0" is perfect match
            if (confidence < 100):
                id = names[id]
                confidence_val = confidence
                confidence = "  {0}%".format(round(100 -confidence))
                
                if round(100-confidence_val) > 25:
                    name_detected[id] = 1
                
            else:
                id = "unknown"
                confidence = "  {0}%".format(round(100 -confidence))
                
                name_detected["None"] = 1

            cv2.putText(img, str(id), (x+5,y-5), font, 1, (255,255,255), 2)
            cv2.putText(img, str(confidence), (x+5,y+h-5), font, 1, (255,255,0), 1)
        cv2.namedWindow('camera')
        cv2.moveWindow('camera', 100, 300)

        cv2.imshow('camera',img)

        k = cv2.waitKey(10) & 0xff # Press 'ESC' for exiting video
        if k == 27:
            break
        
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
    
# Do a bit of cleanup
print("\n [INFO] Exiting Program and cleanup stuff")
cam.release()
cv2.destroyAllWindows()
