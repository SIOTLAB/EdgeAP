import cv2
import os
import sys
import argparse
import json
from time import perf_counter

# CLI options
argparser = argparse.ArgumentParser(description='Collect images for a particular user')
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
        names = c["ids"]
except Exception as e:
    print(e)
    print("Error parsing config file", file=sys.stderr)
    sys.exit(-1)

# Connect to camera and load classifier
cam = cv2.VideoCapture(0)
cam.set(3,640) #height
cam.set(4,480) #width
face_detector = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")

# get id from user
print("User IDs:")
for i in range(len(names)):
        print("\t{}: {}".format(i+1,names[i]))
face_id = input("\nPlease input User ID: ")

num_pics = input("\nEnter number of images to take: ")

if (not os.path.isdir("./dataset")):
        os.mkdir("dataset")

print("\n [INFO] please look directly into the camera.")

start = perf_counter()

count = 1

while(True):
	ret, img = cam.read()
	img = cv2.flip(img,1) # flip image correctly
	gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
	faces = face_detector.detectMultiScale(gray,1.3,5)
	for (x,y,w,h) in faces:
		print("Capturing image " + str(count))
		cv2.rectangle(img,(x,y),(x+w,y+h),(255,0,0),2)
		count += 1
		# save the captured image into the datasets folder
		#cv2.imwrite("dataset/User." + str(face_id) + "." + str(count) + "lq.jpg", gray[y:y+h,x:x+w], [cv2.IMWRITE_JPEG_QUALITY, 75])
		cv2.imwrite("dataset/User." + str(face_id) + "." + str(count) + ".jpg", gray[y:y+h,x:x+w])
		cv2.imshow("image", img)
	k = cv2.waitKey(100) & 0xff  #Press "ESC" to exit the video
	if k == 27:		# if it doesn't detect a face, exit after 27 seconds(?)
		break
	elif count >= int(num_pics): 	# take specified number of face samples and stop the video
		break

end = perf_counter()
exec_time = (end-start)/60.0
print("Program took " + str(exec_time) + " minutes to run.")

print("\n [INFO] Exiting Program  & cleanup stuff")
cam.release()  
