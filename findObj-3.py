# import the necessery packages
from collections import deque
import paho.mqtt.client as mqtt
from imutils.video import VideoStream
import cv2
import argparse
import urllib
import numpy as np
import imutils
import time

vs = urllib.urlopen('http://192.168.0.175:9601/stream')
bytes = ''
colorLower = (33, 80, 40)
colorUpper = (102, 255, 255)
pts = deque(maxlen=1024)

# define the lower and upper boundaries of the "green"
# ball in the HSV color spacem then initialize the list of tracked points

# allow the camera or video file to warm up
time.sleep(2.0)

client = mqtt.Client(client_id="cScorpy", clean_session=True, userdata=None)
print("CONNECTING....")
client.connect("192.168.0.84", 1883,80)
print("CONNECTED")

# keep looping
client.loop_start()

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
		blurred = cv2.GaussianBlur(frame, (11, 11), 0)
		hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
		
		# construct a mask for the color , then perform
		# a series of dilations and erosions to remove any small
		# blobs left in the mask
		mask = cv2.inRange(hsv, colorLower, colorUpper)
		mask = cv2.erode(mask, None, iterations=2)
		mask = cv2.dilate(mask, None, iterations=2)
		#find contours in the mask and initialize the current
		#(x, y) center of the ball
		cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
		cnts = imutils.grab_contours(cnts)
		center = None
		r = False
		l = False
		# only proceed if at least one contour was found
		if len(cnts) > 0:
			#find the largest contour in the mask, then use
			# it to compute the minimum enclosing circle and
			# centroid
			c = max(cnts, key=cv2.contourArea)
			((x, y), radius) = cv2.minEnclosingCircle(c)
			M = cv2.moments(c)
			x = int(M["m10"] / M["m00"])
			y = int(M["m01"] / M["m00"])
			center = (x,y)
			if radius > 10:
				# draw the circle and centroid on the frame,
				# then update the list of tracked points
				cv2.circle(frame, (int(x), int(y)), int(radius), (0, 255, 255), 2)
				cv2.circle(frame, center, 5, (0, 0, 255), -1)
			if x < 250 and not r:
				r = True
				l = False
				client.publish("Scorpy/object", "LEFT")
				#client.publish("cam/center", "STOP")
				print("Left", x, y, radius)
			if x > 350 and not l:
				l = True
				r = False
				client.publish("Scorpy/object", "RIGHT")
				#client.publish("cam/center", "STOP")
				print("Right", x,y,radius)
			if x > 250 and x < 350:
				l = False
				r = False
				if radius < 30:
					client.publish("Scorpy/object", "FRONT")
					print ("Forward", x, y, radius)
				else:
					client.publish("Scorpy/object", "CLOSE")
					print ("the object is closely", x, y, radius)
			# only proceed if the radius meets a minimum size
			# update the points queue
			pts.appendleft(center)
			# loop over the set of tracked points
			for i in xrange(1, len(pts)):
				# if either of the tracked points are None, ignore
				# them
				if pts[i - 1] is None or pts[i] is None:
					continue
			# otherwise, compute the th ickness of the line and
			# draw the connecting lines
			#thickness = int(np.sqrt(1024) / float(i + 1)) * 2.5)
			#cv2.line(frame, pts[i - 1], pts[i], (0, 0, 255), thickness)
		else:
			client.publish("Scorpy/object", "STOP")
			print("Stop")
		# show the frame to our screen
		cv2.imshow("Frame", frame)
		key = cv2.waitKey(1) & 0xFF
		# if the 'q' key is pressed, stop the loop
		if key == ord("q"):
			break
# cleanup the camera and close any open windows
cv2.destroyAllWindows()
