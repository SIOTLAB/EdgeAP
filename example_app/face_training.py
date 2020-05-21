import cv2
import numpy as np
from PIL import Image
import os
import re

if(not os.path.isdir("./trainer")):
	os.mkdir("trainer")

path = "dataset"

recognizer = cv2.face.LBPHFaceRecognizer_create()
detector = cv2.CascadeClassifier("haarcascade_frontalface_default.xml");

def getImagesAndLabels(path):
	# Pattern specifies the amount of images to use for each user during training
	# i.e. r'User\..\.[0-9]{1,2}\..*' will get images 1-99 for all users
	# i.e. r'User\..\.[0-9]{1,3}\..*' will get images 1-999 for all users
	pattern = r'User\..\.[0-9]{1,3}\..*'
	reg = re.compile(pattern)
	imagePaths = [os.path.join(path,f) for f in os.listdir(path) if reg.fullmatch(f)]
	faceSamples = []
	ids = []

	for imagePath in imagePaths:
		PIL_img  = Image.open(imagePath).convert('L') #converting to grayscale
		img_numpy = np.array(PIL_img,"uint8")

		id = int(os.path.split(imagePath)[-1].split(".")[1])
		faces = detector.detectMultiScale(img_numpy)

		for (x,y,w,h) in faces:
			faceSamples.append(img_numpy[y:y+h,x:x+w])
			ids.append(id)
	return faceSamples, ids

print("\n [INFO] Training faces. It will take a few seconds to do this....")
faces, ids = getImagesAndLabels(path)
recognizer.train(faces, np.array(ids))

# save the trained model
recognizer.write("trainer/trainer.yml")

# print the number of faces trained and then end the program
print("\n [INFO] {0} faces trained. Exiting the program now...".format(len(np.unique(ids))))
