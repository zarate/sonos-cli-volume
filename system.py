import Callable
import platform
import os

class system:
	
	def save(file_name, content):

		file_path = system.get_app_data_folder() + "/" + file_name

		file = open(file_path, "w")
		file.write(content)
		file.close()

	def get_app_data_folder():

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

	save = Callable.Callable(save)
	get_app_data_folder = Callable.Callable(get_app_data_folder)
	get_system_app_data_folder = Callable.Callable(get_system_app_data_folder)
	get_system_env = Callable.Callable(get_system_env)