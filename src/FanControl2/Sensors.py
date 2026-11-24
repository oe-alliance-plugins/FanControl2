from .globals import FCGlobals


class Sensors:  # (type, name, unit, directory) - (type, name, unit, fanid) - TYPE_FAN_RPM = 1
	TYPE_TEMPERATURE = 0

	def __init__(self):  # (type, name, unit, sensor_specific_dict/list)
		self.sensors_list = []
		self.addSensors()

	def getSensorsCount(self, type=None):
		if type is None:
			return len(self.sensors_list)
		count = 0
		for sensor in self.sensors_list:
			if sensor[0] == type:
				count += 1
		return count

	def getSensorsList(self, type=None):  # returns a list of sensorids of type "type"
		if type is None:
			return list(range(len(self.sensors_list)))
		items = []
		for sensorid in range(len(self.sensors_list)):
			if self.sensors_list[sensorid][0] == type:
				items.append(sensorid)
		return items

	def getSensorType(self, sensorid):
		return self.sensors_list[sensorid][0]

	def getSensorName(self, sensorid):
		return self.sensors_list[sensorid][1]

	def getSensorDir(self, sensorid):
		return self.sensors_list[sensorid][3]

	def getSensorValue(self, sensorid):
		value = -1
		sensor = self.sensors_list[sensorid]
		if sensor[0] == self.TYPE_TEMPERATURE:
			with open(f"{sensor[3]}/value") as f:
				try:
					value = int(f.readline().strip())
				except Exception:
					pass
		return value

	def addSensors(self):
		from os import listdir
		from os.path import exists
		sensor_path = "/proc/stb/sensors"
		if exists(sensor_path):
			sd = []
			sd = listdir(sensor_path)
			sd.sort()
			for dirname in sd:
				if dirname.find("temp", 0, 4) == 0:
					with open(f"{sensor_path}/{dirname}/name") as f:
						name = f.readline().strip()
					with open(f"{sensor_path}/{dirname}/unit") as f:
						unit = f.readline().strip()
					self.sensors_list.append((self.TYPE_TEMPERATURE, name, unit, f"{sensor_path}/{dirname}"))


sensors = Sensors()
FCGlobals.sensors = sensors
