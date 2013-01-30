# with much help and inspiration from
# Miranda UPnP tool:
# http://code.google.com/p/mirandaupnptool/

import socket
import struct
import time
import urllib2
from urlparse import urlparse
from time import sleep
from thread import *
from xml.etree import ElementTree as ET

MCAST_GRP = "239.255.255.250"
MCAST_PORT = 1900
MAX_RESPONSE_TIME = 10 # seconds
RENDER_CONTROL_SCHEMA = "urn:schemas-upnp-org:service:RenderingControl:1"
NOTIFY_ANSWER = "NOTIFY"
SEARCH_ANSWER = "HTTP/1.1 200 OK"
NS = "{urn:schemas-upnp-org:device-1-0}"


class listen:

	def __init__(self):
		start_new_thread(self.read, ())

	def read(self):

		mreq = struct.pack("4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
		
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		sock.bind(('', MCAST_PORT))		
		sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

		while True:

			msg = message(sock.recv(10240))

			if(msg.interesting()):

				root = ET.fromstring(urllib2.urlopen(msg.url()).read())
				services = root.findall(".//" + NS + "service")

				for service in services:

					if(service.find(NS + "serviceType").text == RENDER_CONTROL_SCHEMA):

						url = urlparse(msg.url())

						controlurl = url.scheme + "://" + url.netloc + service.find(NS + "controlURL").text

						print "NAME: " + root.find(NS + "device/" + NS + "roomName").text
						print "Control URL: " + controlurl

				

class search:

	def __init__(self):

		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		sock.bind(('', MCAST_PORT))

		request = "M-SEARCH * HTTP/1.1\r\n"\
				"HOST: " + MCAST_GRP + ":" + str(MCAST_PORT) + "\r\n"\
				"MAN: \"ssdp:discover\"\r\n"\
				"MX: " + str(MAX_RESPONSE_TIME) + "\r\n"\
				"ST: " + RENDER_CONTROL_SCHEMA + "\r\n"\
				"\r\n"

		print "*************"
		print request
		print "*************"

		sock.sendto(request, (MCAST_GRP, MCAST_PORT))

class message:
	
	_interesting = False
	_url = None

	def __init__(self, data):

			lines = data.split("\r\n")

			# we act on both on automated messages or messages that came from our search
			if( lines[0].upper().startswith(NOTIFY_ANSWER) or lines[0].upper().startswith(SEARCH_ANSWER) ):

				headers = self.parse(data)

				if(headers["NT"] == RENDER_CONTROL_SCHEMA or headers["ST"] == RENDER_CONTROL_SCHEMA):

					self._url = headers["LOCATION"]
					self._interesting = True

	def interesting(self):
		return self._interesting

	def url(self):
		return self._url

	def parse(self, data):

		# we add here the empty headers we are after
		# so python doesn't complain of invalid
		# access when one of them is not in the dictionary

		headers = {"NT": "", "ST": ""}

		lines = data.split("\r\n")

		for line in lines:

			#  discard empty lines
			if not line.strip():
				continue

			# extract header and value
			bits = line.split(":")

			header = bits.pop(0).upper()
			value = ":".join(bits).strip()

			headers[header] = value

		return headers


listen()
search()

start_time = time.time();

# main app loop
while True:
	sleep(0.1)

	if(time.time() - start_time > MAX_RESPONSE_TIME):

		print "ENOUGH WAITING"
		break