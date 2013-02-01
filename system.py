import Callable

import platform
import os
import socket

class system:
	
	def save_file(file_name, content):

		file_path = system.get_app_data_folder() + "/" + file_name

		file = open(file_path, "w")
		file.write(content)
		file.close()

	def read_files():

		# returns FULL PATHS to the files
		app_data_folder = system.get_app_data_folder()
		return [app_data_folder + "/" + name for name in os.listdir(app_data_folder) if os.path.isfile(app_data_folder + "/" + name)]

	def get_app_data_folder():

		# todo, using "." to hide the folder is only Linux-friendly,
		# but not Win / OSX
		app_data_folder = system.get_system_app_data_folder() + "/.sonos_cli"

		if not os.path.exists(app_data_folder):
			os.makedirs(app_data_folder)

		return app_data_folder

	def get_system_app_data_folder():

		# OS-specific paths taken from here:
		# http://stackoverflow.com/questions/57019/where-should-cross-platform-apps-keep-their-data
		return {
			"Windows": system.get_system_env("APPDATA"),
			"Darwin": os.path.expanduser("~") + "/Library/Application Support",
			"Linux": os.path.expanduser("~")
		}.get(platform.system(), False)

	def get_system_env(env):

		try:
			return os.environ[env]
		except KeyError:
			return False

	def reuse_port_type():

		# THANK YOU ATIKAT, STACKOVERFLOW AND GOOGLE:
		# http://stackoverflow.com/questions/7342322/bind-to-mdns-multicast-address-on-mac-os-x
		return {
			"Darwin": socket.SO_REUSEPORT
		}.get(platform.system(), socket.SO_REUSEADDR)

	save_file = Callable.Callable(save_file)
	read_files = Callable.Callable(read_files)
	get_app_data_folder = Callable.Callable(get_app_data_folder)
	get_system_app_data_folder = Callable.Callable(get_system_app_data_folder)
	get_system_env = Callable.Callable(get_system_env)
	reuse_port_type = Callable.Callable(reuse_port_type)