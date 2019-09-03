# import the necessery packages
from collections import deque
import paho.mqtt.client as mqtt
from imutils.video import VideoStream
import cv2
import argparse
import matplotlib
from matplotlib.pyplot import imshow
from matplotlib import pyplot as plt
import urllib
import numpy as np
import imutils
import time
import math

#vs = urllib.urlopen('http://192.168.0.175:9601/stream')
vs = urllib.urlopen('http://192.168.43.136:9601/stream')
bytes = ''
pink_colorLower = (135, 48, 31)
pink_colorUpper = (167, 255, 255)
green_colorLower = (55, 40, 40)
green_colorUpper = (79, 255, 255)
leds_colorLower = (95, 0, 242)
leds_colorUpper = (145,255,255)
whyte_colorLower = (0,0,240)
whyte_colorUpper =(0,255,255)
kernel_size = 5
pts = deque(maxlen=1024)
x,y = [],[]
color_blue = (255,0,0)
color_yellow = (0,255,255)
color_red = (0,0,255)
imgread = False
# define the lower and upper boundaries of the "green"
# ball in the HSV color spacem then initialize the list of tracked points

# allow the camera or video file to warm up
time.sleep(2.0)

client = mqtt.Client(client_id="cScorpy", clean_session=True, userdata=None)
print("CONNECTING....")
#client.connect("192.168.0.84", 1883,80)
client.connect("192.168.43.164", 1883,80)
print("CONNECTED")

# keep looping
while True:
	# grab the current frame
	# frame = vs.read()
	bytes += vs.read(1024)
	a = bytes.find('\xff\xd8')
	b = bytes.find('\xff\xd9')
	if a != -1 and b != -1:
		jpg = bytes[a:b + 2]
		bytes = bytes[b + 2:]
		img = cv2.imdecode(np.fromstring(jpg, dtype=np.uint8),1)
		#resize the frame, blur it, and convert it to the HSV
		#color space
		frame = imutils.resize(img, width=600)
		blur = cv2.GaussianBlur(frame, (kernel_size, kernel_size), 0)
		hsv = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)
		# construct a mask for the color , then perform
		# a series of dilations and erosions to remove any small
		# blobs left in the mask
		green_mask = cv2.inRange(hsv, whyte_colorLower, whyte_colorUpper)
		leds_mask = cv2.inRange(hsv, leds_colorLower, leds_colorUpper)
		mask = cv2.bitwise_or(leds_mask, green_mask)
		mask = cv2.erode(mask, None, iterations=2)
		mask = cv2.dilate(mask, None, iterations=2)
		gray = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
		edges = cv2.Canny(gray,150,200,apertureSize = 3)
		
		cnts, hierarchy = cv2.findContours( mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
		r = False
		l = False
		# sort contours in loop
		lst=[]
		for cnt in cnts:
			rect = cv2.minAreaRect(cnt) # to input box
			box = cv2.boxPoints(rect) # looks keypoints in the box
			box = np.int0(box) # coordinats
			center = (int(rect[0][0]),int(rect[0][1]))
			area = int(rect[1][0]*rect[1][1]) # calculate square of box in contours
			
			edge1 = np.int0((box[1][0] - box[0][0],box[1][1]-box[0][1]))
			edge2 = np.int0((box[2][0]-box[1][0],box[2][1]-box[1][1]))
			# calculate more vector
			usedEdge = edge1
			if cv2.norm(edge2) > cv2.norm(edge1):
				usedEdge= edge2
			reference = (1,0) # gorizont vector
			angle = 180.0/math.pi*math.acos((reference[0]*usedEdge[0]+reference[1]*usedEdge[1]) / (cv2.norm(reference)*cv2.norm(usedEdge)))
			
			if area > 4000:
				cv2.drawContours( frame, [box], 0, (color_blue), 2)
				cv2.circle(frame,center, 5, color_yellow,2) # draw circle
				cv2.putText(frame,"%d" %int(angle), (center[0]+20, center[1]-20), cv2.FONT_HERSHEY_SIMPLEX, 1, color_yellow,2)
				lines = cv2.HoughLines(edges,1,np.pi/180,275)
				lst.append(center)
				lst.append(int(angle))
		cv2.imshow("frame",frame)
		print len(lst)
		print lst
		#if len(lst)>4:
		#	print ("find additional line-box")
		if len(lst)>=4:
			corsR=lst[3]
			corsL=lst[1]
			xR=lst[2]
			xL=lst[0]
			xR,yR=lst[2]
			xL,yL=lst[0]
			print corsL,corsR
			print xL,xR
			M=((xL+xR)/2)
			L=xR-xL
			if (L<0):
				corsR=lst[1]
				corsL=lst[3]
				xR=lst[0]
				xL=lst[2]
				xR,yR=lst[0]
				xL,yL=lst[2]
				print corsL,corsR
				print xL,xR
				M=((xL+xR)/2)
				L=xR-xL
			print ">=4"
			print "L=",L
			print "M=",M
			if (L>280):
				print("on course near")
				client.publish("Scorpy/object", "CLOSE")
			elif (M>250 and M<350):	
				print("robot on far distance")
				client.publish("Scorpy/object", "FRONT")
			elif (M>350):
				print("moved at right")
				client.publish("Scorpy/object", "RIGHT")
			elif (M<250):
				print("moved at left")
				client.publish("Scorpy/object", "LEFT")
		elif len(lst)==2:
			cors=lst[1]
			x=lst[0]
			x,y=lst[0]
			print "=2"
			print cors
			print x
			print("only one line was finded")
			if (x>200 and x<400):
				print("on course at one line")
				client.publish("Scorpy/object", "FRONT")
			elif(x>400):
				print("one line at right")
				client.publish("Scorpy/object", "LEFT")
			elif (x<200):
				print("one line at left")
				client.publish("Scorpy/object", "RIGHT")
			else:
				print("not on course")
				client.publish("Scorpy/object", "BACK")
		else:
			print("absense")
			client.publish("Scorpy/object", "STOP")
						
	key = cv2.waitKey(1) & 0xFF
	# if the 'q' key is pressed, stop the loop
	if key == ord("q"):
		break
# cleanup the camera and close any open windows
cv2.destroyAllWindows()
