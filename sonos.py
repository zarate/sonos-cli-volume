# With much help and inspiration from:
#
# Miranda UPnP tool:
# http://code.google.com/p/mirandaupnptool/
#
# UPnP inspector
# https://launchpad.net/ubuntu/+source/upnp-inspector

import Callable
import system

import socket
import struct
import time
import urllib2
import os, os.path
import sys
import getopt
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

	def __str__(self):
		return "Device: [name: " + name + ", base_url: " + base_url + "]"

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

	def from_xml(xml):

		name = xml.find("name").text
		base_url = xml.find("baseUrl").text
		control_url = xml.find("controlUrl").text
		min_vol = xml.find("minVol").text
		max_vol = xml.find("maxVol").text

		return device(name, base_url, control_url, min_vol, max_vol)

	to_xml = Callable.Callable(to_xml)
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
		
		app_data_folder = system.system.get_app_data_folder()

		# TODO:, we should only count here for device files (.xml)
		return len(management.get_devices()) > 0

	def add_device(new_device):

		url = urlparse(new_device.base_url)

		file_name = url.netloc.replace(".", "_").replace(":", "_") + ".xml"

		print "Adding device: " + new_device.name

		system.system.save_file(file_name, device.to_xml(new_device))

	def get_devices():

		files = system.system.read_files()

		devices = []

		for device_file in files:

			content = open(device_file, "r").read()
			new_device = device.from_xml(ET.fromstring(content))
			devices.append(new_device)

		return devices

	has_configuration = Callable.Callable(has_configuration)
	add_device = Callable.Callable(add_device)
	get_devices = Callable.Callable(get_devices)

def get_volumes():

	volumes = {
		"kill": 0,
		"shutup": 0,
		"quiet": 0.2,
		"low": 0.2,
		"meeting": 0.2,
		"please": 0.2,
		"acceptable": 0.4,
		"normal": 0.4,
		"average": 0.4,
		"high": 0.8
	}

	return volumes

def list_devices():

	devices = management.get_devices()

	if len(devices) <= 0:

		print "No stored devices, try searching first (or again!)"

	else:

		print "List of current devices (search again if this is not what you expect):"
		for device in devices:
			print "\t" + device.name + " (" + device.base_url + ")"

def list_volumes():

	# TODO: print in ASC order by value
	print "List of available volumes:"

	for key in get_volumes():
		print key

def search_devices():
	listen()
	search()

	start_time = time.time();

	while True:
		sleep(0.1)

		if(time.time() - start_time > MAX_RESPONSE_TIME):

			print "Search is over"
			break

def print_help():
	print "The manual:"
	print "\tUsage: sonos.py DEVICE VOLUME"
	print "\tTip #1: You can pass a partial match for the DEVICE name"
	print "\tTip #2: You can pass DEVICE VOLUME or VOLUME DEVICE, doesn't matter"
	print ""
	print "\t-l, --list: prints the list of devices available"
	print "\t-v, --volume: list available volumes"
	print "\t-s, --search: searches for devices"
	print "\t-h, --help: print this help"

def main(argv):

	if len(sys.argv) <= 0:

		print "No arguments passed, don't know what to do, please RTM"
		print_help()
		sys.exit(1)

	try:
		opts, args = getopt.getopt(argv, "lvsh", ["list", "volume", "search", "help"])

	except getopt.GetoptError:

		print "Sorry, can't really work out what you mean"
		print_help()
		sys.exit(2)

	for opt, arg in opts:

		if opt in ("-l", "--list"):
			list_devices()

		elif opt in ("-v", "--volume"):
			list_volumes()

		elif opt in ("-s", "--search"):
			search_devices()

		elif opt in ("-h", "--help"):
			print_help()
			sys.exit(0)

# let's get the party started
if __name__ == "__main__":
	main(sys.argv[1:])