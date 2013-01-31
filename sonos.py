# With much help and inspiration from:
#
# Miranda UPnP tool:
# http://code.google.com/p/mirandaupnptool/
#
# UPnP inspector
# https://launchpad.net/ubuntu/+source/upnp-inspector

import socket
import struct
import time
import urllib2
import Callable
import system
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
NSS = "{urn:schemas-upnp-org:service-1-0}"

class device:

	name = False
	base_url = False
	control_url = False
	min_vol = False
	max_vol = False

	def __init__(self, name, base_url, control_url, min_vol, max_vol):
		self.name = name
		self.base_url = base_url
		self.control_url = control_url
		self.min_vol = min_vol
		self.max_vol = max_vol

	def to_xml(new_device):
		xml_string = "<?xml version=\"1.0\" ?>"\
						"<device>"\
						"<name><![CDATA[" + new_device.name + "]]></name>"\
						"<baseUrl><![CDATA[" + new_device.base_url + "]]></baseUrl>"\
						"<controlUrl><![CDATA[" + new_device.control_url + "]]></controlUrl>"\
						"<minVol><![CDATA[" + new_device.min_vol + "]]></minVol>"\
						"<maxVol><![CDATA[" + new_device.max_vol + "]]></maxVol>"\
						"</device>"
		return xml_string
	to_xml = Callable.Callable(to_xml)

	def from_xml(xml):
		return device("name", "controlurl", "min", "max")
	from_xml = Callable.Callable(from_xml)


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

						# at this point we have a device of the type we are looking for

						url = urlparse(msg.url())
						name = root.find(NS + "device/" + NS + "roomName").text
						base_url = url.scheme + "://" + url.netloc
						control_url = base_url + service.find(NS + "controlURL").text
						service_url = base_url + service.find(NS + "SCPDURL").text
						service_xml = ET.fromstring(urllib2.urlopen(service_url).read())

						variables = service_xml.findall(".//" + NSS + "stateVariable")

						for variable in variables:

							if(variable.find(NSS + "name").text == "Volume"):

								min_vol = variable.find(NSS + "allowedValueRange/" + NSS + "minimum").text
								max_vol = variable.find(NSS + "allowedValueRange/" + NSS + "maximum").text

						found_device = device(name, base_url, control_url, min_vol, max_vol)
						management.add_device(found_device)
				

class search:

	def __init__(self):

		print "Searching for Sonos / UPnP devices. Please wait..."

		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		sock.bind(('', MCAST_PORT))

		request = "M-SEARCH * HTTP/1.1\r\n"\
				"HOST: " + MCAST_GRP + ":" + str(MCAST_PORT) + "\r\n"\
				"MAN: \"ssdp:discover\"\r\n"\
				"MX: " + str(MAX_RESPONSE_TIME) + "\r\n"\
				"ST: " + RENDER_CONTROL_SCHEMA + "\r\n"\
				"\r\n"

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

class management:
	
	def has_configuration():
		return False
	has_configuration = Callable.Callable(has_configuration)

	def add_device(new_device):

		url = urlparse(new_device.base_url)

		file_name = url.netloc.replace(".", "_").replace(":", "_") + ".xml"

		print "Adding device: " + new_device.name

		system.system.save(file_name, device.to_xml(new_device))

	add_device = Callable.Callable(add_device)

if not management.has_configuration():

	listen()
	search()

	start_time = time.time();

	while True:
		sleep(0.1)

		if(time.time() - start_time > MAX_RESPONSE_TIME):

			print "Search is over"
			break

print "DONE"