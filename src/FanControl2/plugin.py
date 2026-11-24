# FanControl2
# joergm6 IHAD
# PID-controller by Lukasz S.

from datetime import date, timedelta
from os import remove, rename, statvfs
from os.path import exists
from subprocess import PIPE, STDOUT, run
from threading import Thread
from time import sleep, strftime, time
from traceback import format_exc

from enigma import eTimer
from Components.ActionMap import ActionMap
from Components.config import config, ConfigSubsection, ConfigInteger, ConfigSlider, ConfigSelection, ConfigYesNo, ConfigText
from Components.Harddisk import harddiskmanager
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Components.Sources.Progress import Progress
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.Setup import Setup
from Screens.MessageBox import MessageBox
from Screens.Console import Console
from Screens import Standby
from Tools.Notifications import AddNotification

from .__init__ import __version__, HeadLine, TempName, _
from .globals import FCGlobals
from .Sensors import sensors

FCGlobals.sensors = sensors

try:
	from Components.SystemInfo import BoxInfo
	FCGlobals.IMAGEDISTRO = BoxInfo.getItem("distro")
	FCGlobals.MACHINE = BoxInfo.getItem("machinebuild")
except ImportError:
	from boxbranding import getImageDistro, getBoxType
	FCGlobals.IMAGEDISTRO = getImageDistro()
	FCGlobals.MACHINE = getBoxType()


def main(session, **kwargs):
	try:
		session.open(FanControl2Plugin)
	except Exception:
		FClog("Pluginexecution failed")


def mainMonitor(session, **kwargs):
	try:
		session.open(FanControl2Monitor)
	except Exception:
		FClog("Pluginexecution failed")


def Test0(wert):
	return (1 if wert <= 0 else wert)


def skal(x, x1, x2, y1, y2):
	if x > x2:
		return y2
	if x < x1:
		return y1
	m = (y2 - y1) / Test0(x2 - x1)
	y = m * x + y1
	return y


def FClog(wert):
	if config.plugins.FanControl.EnableConsoleLog.value:
		print("[FanControl2]", wert)
	while len(FCGlobals.FC2Log) > config.plugins.FanControl.LogCount.value:
		del FCGlobals.FC2Log[5]
	FCGlobals.FC2Log.append(f"{strftime('%H:%M:%S ')}{wert}")
	if config.plugins.FanControl.EnableEventLog.value:
		if Free(config.plugins.FanControl.LogPath.value):
			try:
				with open(f"{config.plugins.FanControl.LogPath.value}FC2events.txt", "a") as f:
					f.write(f"{strftime('%H:%M:%S ')}{wert}\r\n")
			except OSError:
				FCGlobals.FC2Log.append(f"{strftime('%H:%M:%S ')}Event-Log-Error")


def FClogE(wert):
	if config.plugins.FanControl.EnableEventLog.value:
		FClog(wert)


def FCdata():
	if strftime("%M") != FCGlobals.DataMinute and config.plugins.FanControl.EnableDataLog.value:
		FCGlobals.DataMinute = strftime("%M")
		if Free(config.plugins.FanControl.LogPath.value):
			try:
				with open(f"{config.plugins.FanControl.LogPath.value}FC2data.csv", "a") as f:
					f.write(strftime("%Y.%m.%d %H:%M"))
					for count in range(6):
						f.write(f";{str(FCGlobals.FC2werte[count]).replace('.', _('.'))}")
					templist = FCGlobals.sensors.getSensorsList(FCGlobals.sensors.TYPE_TEMPERATURE)
					tempcount = len(templist)
					for count in range(tempcount):
						f.write(f";{FCGlobals.sensors.getSensorValue(count)}")
					f.write("\r\n")
			except OSError:
				FCGlobals.FC2Log.append(f"{strftime('%H:%M:%S ')}Event-Log-Error")


def Free(dir):
	if not exists(dir):
		return False
	s = statvfs(dir)
	return (s.f_bsize * s.f_bavail / 1024 / 1024) > 10


def getVoltage(fanid):
	with open(f"{FCGlobals.FanPath}/fan_vlt") as f:
		return int(f.readline().strip(), 16)


def setVoltage(fanid, value):
	if value > 255:
		return
	with open(f"{FCGlobals.FanPath}/fan_vlt", "w") as f:
		f.write(f"{value:x}")


def getPWM(fanid):
	with open(f"{FCGlobals.FanPath}/fan_pwm") as f:
		return int(f.readline().strip(), 16)


def setPWM(fanid, value):
	if value > 255:
		return
	with open(f"{FCGlobals.FanPath}/fan_pwm", "w") as f:
		f.write(f"{value:x}")


#Configuration
config.plugins.FanControl = ConfigSubsection()

if FCGlobals.IMAGEDISTRO in ('openspa') and FCGlobals.MACHINE in ('vusolo2'):
	config.plugins.FanControl.Fan = ConfigSelection(choices=[("disabled", _("disabled")), ("aus", _("Control disabled")), ("3pin", _("3Pin")), ("4pin", _("4Pin")), ("4pinREG", _("4Pin (PID)"))], default="3pin")
	config.plugins.FanControl.StandbyOff = ConfigSelection(choices=[("false", _("no")), ("true", _("yes")), ("trueRec", _("yes, Except for Recording or HDD"))], default="true")
	config.plugins.FanControl.minRPM = ConfigSlider(default=900, increment=50, limits=(0, 1500))
	config.plugins.FanControl.maxRPM = ConfigSlider(default=1100, increment=50, limits=(500, 6000))
	config.plugins.FanControl.temp = ConfigSlider(default=42, increment=1, limits=(30, 50))
	config.plugins.FanControl.tempmax = ConfigSlider(default=50, increment=1, limits=(35, 55))
	config.plugins.FanControl.pwm = ConfigSlider(default=30, increment=5, limits=(0, 255))
	config.plugins.FanControl.vlt = ConfigSlider(default=30, increment=5, limits=(0, 255))
elif FCGlobals.IMAGEDISTRO in ('openspa') and FCGlobals.MACHINE in ('vuduo2'):
	config.plugins.FanControl.Fan = ConfigSelection(choices=[("disabled", _("disabled")), ("aus", _("Control disabled")), ("3pin", _("3Pin")), ("4pin", _("4Pin")), ("4pinREG", _("4Pin (PID)"))], default="4pin")
	config.plugins.FanControl.StandbyOff = ConfigSelection(choices=[("false", _("no")), ("true", _("yes")), ("trueRec", _("yes, Except for Recording or HDD"))], default="true")
	config.plugins.FanControl.minRPM = ConfigSlider(default=750, increment=50, limits=(0, 1500))
	config.plugins.FanControl.maxRPM = ConfigSlider(default=1100, increment=50, limits=(500, 6000))
	config.plugins.FanControl.temp = ConfigSlider(default=42, increment=1, limits=(30, 50))
	config.plugins.FanControl.tempmax = ConfigSlider(default=50, increment=1, limits=(35, 55))
	config.plugins.FanControl.pwm = ConfigSlider(default=125, increment=5, limits=(0, 255))
	config.plugins.FanControl.vlt = ConfigSlider(default=165, increment=5, limits=(0, 255))
else:
	config.plugins.FanControl.Fan = ConfigSelection(choices=[("disabled", _("disabled")), ("aus", _("Control disabled")), ("3pin", _("3Pin")), ("4pin", _("4Pin")), ("4pinREG", _("4Pin (PID)"))], default="disabled")
	config.plugins.FanControl.StandbyOff = ConfigSelection(choices=[("false", _("no")), ("true", _("yes")), ("trueRec", _("yes, Except for Recording or HDD"))], default="false")
	config.plugins.FanControl.minRPM = ConfigSlider(default=600, increment=50, limits=(0, 1500))
	config.plugins.FanControl.maxRPM = ConfigSlider(default=3000, increment=50, limits=(500, 6000))
	config.plugins.FanControl.temp = ConfigSlider(default=40, increment=1, limits=(30, 50))
	config.plugins.FanControl.tempmax = ConfigSlider(default=50, increment=1, limits=(35, 55))
	config.plugins.FanControl.pwm = ConfigSlider(default=130, increment=5, limits=(0, 255))
	config.plugins.FanControl.vlt = ConfigSlider(default=255, increment=5, limits=(0, 255))
config.plugins.FanControl.ShowError = ConfigSelection(choices=[("false", _("do nothing")), ("true", _("display Info")), ("shutdown", _("Box Shutdown"))], default="true")
config.plugins.FanControl.ShutdownTemp = ConfigInteger(default=65, limits=(50, 80))
config.plugins.FanControl.AddOverheat = ConfigInteger(default=0, limits=(0, 9))
config.plugins.FanControl.DisableDMM = ConfigYesNo(default=False)
config.plugins.FanControl.LogCount = ConfigInteger(default=40, limits=(40, 999))
config.plugins.FanControl.LogPath = ConfigText(default="/tmp/", fixed_size=False)
config.plugins.FanControl.DeleteData = ConfigSelection(choices=[("0", _("no")), ("2", "2"), ("3", "3"), ("7", "7"), ("14", "14"), ("30", "30")], default="14")
config.plugins.FanControl.EnableConsoleLog = ConfigYesNo(default=False)
config.plugins.FanControl.EnableDataLog = ConfigYesNo(default=False)
config.plugins.FanControl.EnableEventLog = ConfigYesNo(default=False)
config.plugins.FanControl.CheckHDDTemp = ConfigSelection(choices=[("false", _("no")), ("true", _("yes")), ("auto", _("auto")), ("never", _("never"))], default="never")
config.plugins.FanControl.MonitorInExtension = ConfigYesNo(default=True)
config.plugins.FanControl.FanControlInExtension = ConfigYesNo(default=True)
config.plugins.FanControl.Multi = ConfigSelection(choices=[("1", "RPM"), ("2", "RPM/2")], default="2")
config.plugins.FanControl.EnableThread = ConfigYesNo(default=True)


def GetFanRPM():
	with open(f"{FCGlobals.FanPath}/fan_speed") as f:
		value = int(f.readline().strip()[:-4])
	value = int(value / int(config.plugins.FanControl.Multi.value))
	if value > 0 and value < 6000:
		FCGlobals.RPMread = 0
	else:
		FCGlobals.RPMread += 1
	return value

# def isDMMdisabled():
# 	value = False
# 	if os.path.exists("/usr/lib/enigma2/python/Components/FanControl.py"):
# 		FCfile = open("/usr/lib/enigma2/python/Components/FanControl.py")
# 		text=FCfile.read()
# 		FCfile.close()
# 		if text.find("#Disabled by FC2 config.misc.standbyCounter.addNotifier") is not -1:
# 			value = True
# 	return value
#
# def disableDMM():
# 	if os.path.exists("/usr/lib/enigma2/python/Components/FanControl.py"):
# 		FCfile = open("/usr/lib/enigma2/python/Components/FanControl.py")
# 		text=FCfile.read()
# 		FCfile.close()
# 		FCfile = open("/usr/lib/enigma2/python/Components/FanControl.py", "w")
# 		text=text.replace("config.misc.standbyCounter.addNotifier","#Disabled by FC2 config.misc.standbyCounter.addNotifier")
# 		text=FCfile.write(text)
# 		FCfile.close()
# 		FClog("Fancontrol disabled - please restart E2")
#
# def enableDMM():
# 	if os.path.exists("/usr/lib/enigma2/python/Components/FanControl.py"):
# 		FCfile = open("/usr/lib/enigma2/python/Components/FanControl.py")
# 		text=FCfile.read()
# 		FCfile.close()
# 		FCfile = open("/usr/lib/enigma2/python/Components/FanControl.py", "w")
# 		text=text.replace("#Disabled by FC2 config.misc.standbyCounter.addNotifier","config.misc.standbyCounter.addNotifier")
# 		text=FCfile.write(text)
# 		FCfile.close()

# the PI controller class


class ControllerPI:
	name = "PI Controller"
	looptime = 0.0
	dt = 0.0
	timer_delay = 0.0
	inputMax = 0.0
	inputError = 0.0
	inputDeadband = 0.0
	integratorOutput = 0.0
	controlSignal = 0.0
	coeffKp = 0.0
	coeffKi = 0.0

	def __init__(self, givenName="PI Controller"):
		self.name = givenName
#		FClogE(f"{self.name} : creating object")

	def ReturnInputError(self):
		return self.inputError

	def ResetIntegrator(self):
		FClogE(f"{self.name} : integrator output {self.integratorOutput:3.2f}")
		self.integratorOutput = 0.0
#		FClog(f"{self.name} : integrator output now 0")

	def ScaleCtlError(self, errval, inputMax):
		if errval == 0:
			return 0
		return skal(abs(errval), 0, inputMax, 0, 100) * (errval / abs(errval))

	def DeadBand(self, errval):
		if abs(errval) < self.inputDeadband:
			FClogE(f"{self.name} : error within bounds {abs(errval):3.2f} % < {self.inputDeadband:3.2f} %, WON'T control")
			return 0.0
		else:
			FClogE(f"{self.name} : error EXCEEDS bounds {abs(errval):3.2f} % > {self.inputDeadband:3.2f} %, will control")
			return errval

	def Integrate(self, errval):
		self.integratorOutput += errval * self.dt
		return self.integratorOutput

	def ControlProcess(self, InputError, integratorOutput):
		return self.coeffKp * InputError + self.coeffKi * integratorOutput

	def ControlLoop(self, ctlInput, ctlFeedback):
		if self.dt < self.timer_delay:
			FClogE(f"{self.name} : WRONG SETTINGS! dt must be >= timer_delay! Adjusted to be same for now.")
			self.dt = self.timer_delay

		self.looptime += self.timer_delay
		if self.looptime < self.dt:
			FClogE(f"{self.name} : NOT calling control, looptime {self.looptime:.0f} < {self.dt:.0f} dt")
			return self.controlSignal
		else:
			FClogE(f"{self.name} : calling control, looptime {self.looptime:.0f} = {self.dt:.0f} dt")
			self.looptime = 0

		self.inputError = ctlInput - ctlFeedback
		FClogE(f"{self.name} : made up Input Error {self.inputError:3.2f}")
		self.inputError = self.ScaleCtlError(self.inputError, self.inputMax)
		FClogE(f"{self.name} : after scale: Input Error {self.inputError:3.2f} %")
		self.inputError = self.DeadBand(self.inputError)
		FClogE(f"{self.name} : after deadband: Input Error {self.inputError:3.2f} %")
		self.integratorOutput = self.Integrate(self.inputError)
		FClogE(f"{self.name} : Integrator output {self.integratorOutput:3.2f} %")
		self.controlSignal = self.ControlProcess(self.inputError, self.integratorOutput)
		FClogE(f"{self.name} : Control Signal {self.controlSignal:3.2f} %")
		return self.controlSignal
# the PI controller class -end


class FanControl2Test(Screen):
	skin = """
		<screen position="center,center" size="630,300" title="Fan Control 2 - Test" >
			<widget source="TextTest1" render="Label" position="5,20" size="620,30" zPosition="10" font="Regular;20" halign="left" valign="center" backgroundColor="#25062748" transparent="1" />
			<widget source="TextTest2" render="Label" position="5,50" size="620,30" zPosition="10" font="Regular;20" halign="left" valign="center" backgroundColor="#25062748" transparent="1" />
			<widget source="TextTest3" render="Label" position="5,80" size="620,30" zPosition="10" font="Regular;20" halign="left" valign="center" backgroundColor="#25062748" transparent="1" />
			<widget source="TextTest4" render="Label" position="5,130" size="620,30" zPosition="10" font="Regular;20" halign="left" valign="center" backgroundColor="#25062748" transparent="1" />
			<widget source="TextTest5" render="Label" position="5,160" size="620,30" zPosition="10" font="Regular;20" halign="left" valign="center" backgroundColor="#25062748" transparent="1" />
			<widget source="TextTest6" render="Label" position="5,190" size="620,30" zPosition="10" font="Regular;20" halign="left" valign="center" backgroundColor="#25062748" transparent="1" />
			<widget source="TextTest7" render="Label" position="5,220" size="620,30" zPosition="10" font="Regular;20" halign="left" valign="center" backgroundColor="#25062748" transparent="1" />
		</screen>"""

	def __init__(self, session, args=0):
		self.session = session
		Screen.__init__(self, session)
		self.timer = eTimer()
		self.timer.callback.append(self.DoTest)
		self.timer.start(1000, True)
		self["TextTest1"] = StaticText()
		self["TextTest2"] = StaticText()
		self["TextTest3"] = StaticText()
		self["TextTest4"] = StaticText()
		self["TextTest5"] = StaticText()
		self["TextTest6"] = StaticText()
		self["TextTest7"] = StaticText()
		self["TextTest1"].setText(_("please wait (until 3min)..."))
		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"ok": self.cancel,
			"cancel": self.cancel
		}, -1)

	def VoltUp(self):
		while GetFanRPM() < 100 and self.i < 255:
			setVoltage(self.id, self.i)
			sleep(0.3)
			self.i += 1

	def VoltDown(self):
		while GetFanRPM() > 100 and self.i > 0:
			setVoltage(self.id, self.i)
			sleep(1)
			self.i -= 1

	def DoTest(self):
		self.id = 0
		self.i = 0
		self.last = 0
		self.rpm = 0
		SaveAktVLT = FCGlobals.AktVLT
		SaveAktPWM = FCGlobals.AktPWM
		SaveFan = config.plugins.FanControl.Fan.value
		config.plugins.FanControl.Fan.value = "aus"
		if SaveFan in ["4pin", "4pinREG"]:
			setPWM(self.id, 0)
			sleep(10)
			while GetFanRPM() < 100 and self.i < 255:
				setPWM(self.id, self.i)
				sleep(0.3)
				self.i += 1
			sleep(2)
			self.last = GetFanRPM()
			self["TextTest1"].setText(_("Min Fan Start {last:d} rpm at PWM={pwm:d}").format(last=self.last, pwm=self.i))
			while GetFanRPM() > 100 and self.i > 1:
				setPWM(self.id, self.i)
				sleep(1)
				self.i -= 1
			ok = "OK" if config.plugins.FanControl.minRPM.value >= self.last else f"!!>{config.plugins.FanControl.minRPM.value:d}"
			self["TextTest2"].setText(_("Min Fan Stop {last:d} rpm at PWM={pwm:d} ({status})").format(last=self.last, pwm=self.i, status=ok))
			setPWM(self.id, 255)
			sleep(6)
			self.rpm = GetFanRPM()
			ok = "OK" if config.plugins.FanControl.maxRPM.value <= self.rpm else f"!!<{config.plugins.FanControl.maxRPM.value:d}"
			self["TextTest3"].setText(_("Max Fan {rpm:d} rpm at PWM=255 ({status})").format(rpm=self.rpm, status=ok))
# extended
			self["TextTest4"].setText(_("Extended Control Range"))
			setPWM(self.id, 0)
			sleep(10)
			self.rpm = GetFanRPM()
			if self.rpm > 0:
				setVoltage(self.id, 0)
				sleep(10)
				self.VoltUp()
				sleep(3)
				self.last = GetFanRPM()
				self["TextTest5"].setText(_("Min Fan Start {last:d} rpm at VLT={voltage:d} and PWM=0").format(last=self.last, voltage=self.i))
				self.VoltDown()
				ok = "OK" if config.plugins.FanControl.minRPM.value >= self.last else f"!!>{config.plugins.FanControl.minRPM.value:d}"
				self["TextTest6"].setText(_("Min Fan Stop {last:d} rpm at VLT={voltage:d} and PWM=0 ({status})").format(last=self.last, voltage=self.i, status=ok))
			setPWM(self.id, 255)
			setVoltage(self.id, 255)
			sleep(6)
			self.rpm = GetFanRPM()
			ok = "OK" if config.plugins.FanControl.maxRPM.value <= self.rpm else f"!!<{config.plugins.FanControl.maxRPM.value:d}"
			self["TextTest7"].setText(_("Max Fan {rpm:d} rpm at PWM=255 and VLT=255 ({status})").format(rpm=self.rpm, status=ok))
		elif SaveFan == "3pin":
			setVoltage(self.id, 0)
			sleep(10)
			self.VoltUp()
			sleep(3)
			self.last = GetFanRPM()
			self["TextTest1"].setText(_("Min Fan Start {last:d} rpm at VLT={voltage:d}").format(last=self.last, voltage=self.i))
			self.VoltDown()
			ok = "OK" if config.plugins.FanControl.minRPM.value >= self.last else f"!!>{config.plugins.FanControl.minRPM.value:d}"
			self["TextTest2"].setText(_("Min Fan Stop {last:d} rpm at VLT={voltage:d} ({status})").format(last=self.last, voltage=self.i, status=ok))
			setVoltage(self.id, 255)
			sleep(6)
			ok = "OK" if config.plugins.FanControl.maxRPM.value <= GetFanRPM() else f"!!<{config.plugins.FanControl.maxRPM.value:d}"
			self["TextTest3"].setText(_("Max Fan {rpm:d} rpm at VLT=255 ({status})").format(rpm=GetFanRPM(), status=ok))
		else:
			self["TextTest1"].setText(_("please set fan type (3Pin or 4Pin)"))
		setVoltage(self.id, SaveAktVLT)
		setPWM(self.id, SaveAktPWM)
		config.plugins.FanControl.Fan.value = SaveFan

	def cancel(self):
		self.close(False, self.session)


class FanControl2Monitor(Screen):
	skin = """
		<screen position="center,center" size="600,260" title="Fan Control 2 - Monitor">
			<widget source="TxtTemp0" render="Label" position="5,30" size="250,25" zPosition="1" font="Regular;17" halign="right" valign="center" backgroundColor="#25062748" transparent="1" />
			<widget source="TxtTemp1" render="Label" position="5,50" size="250,25" zPosition="1" font="Regular;17" halign="right" valign="center" backgroundColor="#25062748" transparent="1" />
			<widget source="TxtTemp2" render="Label" position="5,70" size="250,25" zPosition="1" font="Regular;17" halign="right" valign="center" backgroundColor="#25062748" transparent="1" />
			<widget source="TxtTemp3" render="Label" position="5,90" size="250,25" zPosition="1" font="Regular;17" halign="right" valign="center" backgroundColor="#25062748" transparent="1" />
			<widget source="TxtTemp4" render="Label" position="5,110" size="250,25" zPosition="1" font="Regular;17" halign="right" valign="center" backgroundColor="#25062748" transparent="1" />
			<widget source="TxtTemp5" render="Label" position="5,130" size="250,25" zPosition="1" font="Regular;17" halign="right" valign="center" backgroundColor="#25062748" transparent="1" />
			<widget source="TxtTemp6" render="Label" position="5,150" size="250,25" zPosition="1" font="Regular;17" halign="right" valign="center" backgroundColor="#25062748" transparent="1" />
			<widget source="TxtTemp7" render="Label" position="5,170" size="250,25" zPosition="1" font="Regular;17" halign="right" valign="center" backgroundColor="#25062748" transparent="1" />
			<widget source="TxtHDD" render="Label" position="5,190" size="250,25" zPosition="1" font="Regular;17" halign="right" valign="center" backgroundColor="#25062748" transparent="1" />
			<widget source="TxtFan" render="Label" position="5,210" size="250,25" zPosition="1" font="Regular;17" halign="right" valign="center" backgroundColor="#25062748" transparent="1" />
			<widget name="TxtMinTemp" position="260,20" size="50,12" zPosition="1" font="Regular;12" halign="left" valign="center" backgroundColor="#25062748" transparent="1" />
			<widget source="TxtFC2Temp" render="Label" position="398,20" size="50,12" zPosition="1" font="Regular;17" halign="center" valign="center" backgroundColor="#25062748" transparent="1" />
			<widget name="TxtMaxTemp" position="535,20" size="50,12" zPosition="1" font="Regular;12" halign="right" valign="center" backgroundColor="#25062748" transparent="1" />
			<widget source="ProTemp0" render="Progress" position="260,40" size="325,5" borderWidth="1" />
			<widget source="ProTemp1" render="Progress" position="260,60" size="325,5" borderWidth="1" />
			<widget source="ProTemp2" render="Progress" position="260,80" size="325,5" borderWidth="1" />
			<widget source="ProTemp3" render="Progress" position="260,100" size="325,5" borderWidth="1" />
			<widget source="ProTemp4" render="Progress" position="260,120" size="325,5" borderWidth="1" />
			<widget source="ProTemp5" render="Progress" position="260,140" size="325,5" borderWidth="1" />
			<widget source="ProTemp6" render="Progress" position="260,160" size="325,5" borderWidth="1" />
			<widget source="ProTemp7" render="Progress" position="260,180" size="325,5" borderWidth="1" />
			<widget source="ProHDD" render="Progress" position="260,200" size="325,5" borderWidth="1" />
			<widget source="ProFan" render="Progress" position="260,220" size="325,5" borderWidth="1" />
		</screen>"""

	def __init__(self, session, args=None):
		Screen.__init__(self, session)

		self.temp_timer = eTimer()
		self.temp_timer.callback.append(self.updateTemp)

		for count in range(8):
			self[f"ProTemp{count}"] = Progress()
			self[f"TxtTemp{count}"] = StaticText("")
		self["ProHDD"] = Progress()
		self["TxtHDD"] = StaticText("")
		self["ProFan"] = Progress()
		self["TxtFan"] = StaticText("")
		self["TxtFC2Temp"] = StaticText("")
		self["TxtMinTemp"] = Label("30")
		self["TxtMaxTemp"] = Label("55")
		self["actions"] = ActionMap(["OkCancelActions", "EPGSelectActions"],
		{
			"ok": self.cancel,
			"cancel": self.cancel,
			"info": self.getHDD
		}, -1)
		self.onLayoutFinish.append(self.updateTemp)

	def updateTemp(self):
		templist = FCGlobals.sensors.getSensorsList(FCGlobals.sensors.TYPE_TEMPERATURE)
		tempcount = len(templist)
		for count in range(tempcount):
			tt = FCGlobals.sensors.getSensorValue(count)
			self[f"ProTemp{count}"].value = int((tt - 30) * 100 / (55 - 30))
			if FCGlobals.sensors.getSensorName(count) == "undefined":
				self[f"TxtTemp{count}"].setText(_("{name}   {temperature:02d} C").format(name=TempName[count], temperature=int(tt)))
			else:
				self[f"TxtTemp{count}"].setText(_("{name}   {temperature:02d} C").format(name=FCGlobals.sensors.getSensorName(count), temperature=int(tt)))
		if harddiskmanager.HDDCount() > 0 and len(FCGlobals.AktHDD) > 0:
			if max(FCGlobals.AktHDD) > 0:
				self["ProHDD"].value = int((max(FCGlobals.AktHDD) - 30) * 100 / (55 - 30))
				self["TxtHDD"].setText(_("{name}   {temperature:02d} C").format(name="HDD", temperature=max(FCGlobals.AktHDD)))
			elif config.plugins.FanControl.CheckHDDTemp.value != "never":
				self["TxtHDD"].setText(_("press Info for HDD-Temp"))
		self["TxtFan"].setText(_("Current rpm  {rpm:4d}").format(rpm=FCGlobals.AktRPM))
		self["ProFan"].value = int((FCGlobals.AktRPM - config.plugins.FanControl.minRPM.value) * 100 / Test0(config.plugins.FanControl.maxRPM.value - config.plugins.FanControl.minRPM.value))
		if tempcount > 1:
			self["TxtFC2Temp"].setText(f"{FCGlobals.AktTemp:4.1f}")
		self.temp_timer.start(2000, True)

	def cancel(self):
		self.close(False, self.session)

	def getHDD(self):
		if harddiskmanager.HDDCount() > 0 and config.plugins.FanControl.CheckHDDTemp.value != "never":
			GetHDDtemp(True)
			for hdd in harddiskmanager.HDDList():
				if hdd[1].model().startswith("ATA"):
					if hdd[1].isSleeping():
						(stat, wert) = getstatusoutput(f"hdparm -y {hdd[1].getDeviceName()}")


class FanControl2SpezialSetup(Setup):
	def __init__(self, session, args=None):
		self.HDDmode = config.plugins.FanControl.CheckHDDTemp.value
		Setup.__init__(self, session, "FanControl2Special", plugin="Extensions/FanControl2", PluginLanguageDomain="FanControl2")
		self.addSaveNotifier(self.prepareSave)

	def keySelect(self):
		if self.getCurrentItem() == config.plugins.FanControl.LogPath:
			from Screens.LocationBox import LocationBox
			self.session.openWithCallback(self.dirSelected, LocationBox, text=_("Choose path"), filename="", currDir=config.plugins.FanControl.LogPath.value, minFree=50)
			return
		Setup.keySelect(self)

	def dirSelected(self, dir):
		if dir is not None and dir != "?":
			if dir[-1:] != "/":
				dir += "/"
			config.plugins.FanControl.LogPath.value = dir
		self["config"].invalidateCurrent()
		self.changedEntry()

	def prepareSave(self):
		if config.plugins.FanControl.LogPath.value[-1:] != "/":
			config.plugins.FanControl.LogPath.value += "/"
		if config.plugins.FanControl.CheckHDDTemp.value == "auto" and config.plugins.FanControl.CheckHDDTemp.value != self.HDDmode:
			FCGlobals.disableHDDread = True
		self.ensureDataLog()

	def changedEntry(self):
		self.ensureDataLog()
		Setup.changedEntry(self)

	def ensureDataLog(self):
		if not config.plugins.FanControl.EnableDataLog.value:
			return
		if config.plugins.FanControl.LogPath.value[-1:] != "/":
			config.plugins.FanControl.LogPath.value += "/"
		if not exists(f"{config.plugins.FanControl.LogPath.value}FC2data.csv") and Free(config.plugins.FanControl.LogPath.value):
			try:
				with open(f"{config.plugins.FanControl.LogPath.value}FC2data.csv", "w") as f:
					f.write(HeadLine)
			except OSError:
				FClog("Data-Log-Error")


class FanControl2Plugin(Setup):
	skin = """
		<screen position="center,center" size="600,450" title="Fan Control 2">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/key_info.png" position="560,0" zPosition="4" size="35,25"  transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/key_menu.png" position="560,20" zPosition="4" size="35,25"  transparent="1" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
			<widget source="Version" render="Label" position="5,430" size="60,20" zPosition="1" font="Regular;11" halign="left" valign="center" backgroundColor="#25062748" transparent="1" />
			<widget name="config" position="10,50" size="580,200" scrollbarMode="showOnDemand" />
			<widget name="footnote" position="0,0" size="0,0" />
			<widget name="description" position="0,0" size="0,0" />
			<ePixmap position="20,260" size="560,3" pixmap="skin_default/div-h.png" transparent="1" alphatest="on" />
			<widget source="introduction" render="Label" position="5,262" size="580,30" zPosition="10" font="Regular;21" halign="center" valign="center" backgroundColor="#25062748" transparent="1" />
			<ePixmap position="20,290" size="560,3" pixmap="skin_default/div-h.png" transparent="1" alphatest="on" />
			<widget source="TxtTemp" render="Label" position="5,310" size="200,25" zPosition="1" font="Regular;17" halign="right" valign="center" backgroundColor="#25062748" transparent="1" />
			<widget source="TxtZielRPM" render="Label" position="5,330" size="200,25" zPosition="1" font="Regular;17" halign="right" valign="center" backgroundColor="#25062748" transparent="1" />
			<widget source="TxtRPM" render="Label" position="5,350" size="200,25" zPosition="1" font="Regular;17" halign="right" valign="center" backgroundColor="#25062748" transparent="1" />
			<widget source="TxtVLT" render="Label" position="5,370" size="200,25" zPosition="1" font="Regular;17" halign="right" valign="center" backgroundColor="#25062748" transparent="1" />
			<widget source="TxtPWM" render="Label" position="5,390" size="200,25" zPosition="1" font="Regular;17" halign="right" valign="center" backgroundColor="#25062748" transparent="1" />
			<widget source="PixTemp" render="Progress" position="210,320" size="375,5" borderWidth="1" />
			<widget source="PixZielRPM" render="Progress" position="210,340" size="375,5" borderWidth="1" />
			<widget source="PixRPM" render="Progress" position="210,360" size="375,5" borderWidth="1" />
			<widget source="PixVLT" render="Progress" position="210,380" size="375,5" borderWidth="1" />
			<widget source="PixPWM" render="Progress" position="210,400" size="375,5" borderWidth="1" />
			<widget source="TxtERR" render="Label" position="5,410" size="200,25" zPosition="1" font="Regular;17" halign="right" valign="center" backgroundColor="#25062748" transparent="1" />
			<widget source="PixERR" render="Progress" position="210,420" size="375,5" borderWidth="1" />
			<widget source="T10ERR" render="Label" position="570,422" size="40,20" zPosition="1" font="Regular;11" halign="left" valign="center" backgroundColor="#25062748" transparent="1" />
		</screen>"""

	def __init__(self, session, args=0):
		Setup.__init__(self, session, "FanControl2Main", plugin="Extensions/FanControl2", PluginLanguageDomain="FanControl2")
		self.fan_timer = eTimer()
		self.fan_timer.callback.append(self.updateFanStatus)
		FCGlobals.LastVLT = config.plugins.FanControl.vlt.value
		FCGlobals.LastPWM = config.plugins.FanControl.pwm.value
		self["key_red"] = self["red"] = StaticText(_("Cancel"))
		self["key_green"] = self["green"] = StaticText(_("Save"))
		self["key_yellow"] = self["yellow"] = StaticText(_("Check"))
		self["key_blue"] = self["blue"] = StaticText(_("Help"))
		self["introduction"] = StaticText()
		self["Version"] = StaticText(f"V {__version__}")
		self["TxtTemp"] = StaticText()
		self["TxtZielRPM"] = StaticText()
		self["TxtRPM"] = StaticText()
		self["TxtVLT"] = StaticText()
		self["TxtPWM"] = StaticText()
		self["PixTemp"] = Progress()
		self["PixZielRPM"] = Progress()
		self["PixRPM"] = Progress()
		self["PixVLT"] = Progress()
		self["PixPWM"] = Progress()
		self["PixERR"] = Progress()
		self["TxtERR"] = StaticText()
		self["T10ERR"] = StaticText()
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "MenuActions", "EPGSelectActions"],
		{
			"ok": self.keySelect,
			"cancel": self.keyCancel,
			"red": self.keyCancel,
			"green": self.keySave,
			"yellow": self.pruefen,
			"blue": self.help,
			"menu": self.SetupMenu,
			"info": self.monitor
		}, -1)

		if self.selectionChanged not in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()
		self.onLayoutFinish.append(self.updateFanStatus)

	def changedEntry(self):
		Setup.changedEntry(self)
		self.selectionChanged()

	def selectionChanged(self):
		Setup.selectionChanged(self)
		if "introduction" not in self:
			return
		self["introduction"].setText(_("Current value: {value}").format(value=self.getCurrentValue()))
		if self["config"].getCurrentIndex() > 4:
			if FCGlobals.LastVLT != config.plugins.FanControl.vlt.value or FCGlobals.LastPWM != config.plugins.FanControl.pwm.value:
				FCGlobals.LastVLT = config.plugins.FanControl.vlt.value
				FCGlobals.LastPWM = config.plugins.FanControl.pwm.value
				FCGlobals.AktVLT = FCGlobals.LastVLT
				FCGlobals.AktPWM = FCGlobals.LastPWM
				id = 0
				setVoltage(id, FCGlobals.LastVLT)
				setPWM(id, FCGlobals.LastPWM)
				FCGlobals.AktRPM = GetFanRPM()
		d = config.plugins.FanControl.tempmax.value - config.plugins.FanControl.temp.value
		if d < 5:
			if config.plugins.FanControl.temp.value + d < 55:
				config.plugins.FanControl.tempmax.value = config.plugins.FanControl.temp.value + 5
			else:
				config.plugins.FanControl.temp.value = config.plugins.FanControl.tempmax.value - 5

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def updateFanStatus(self):
		if config.plugins.FanControl.Fan.value == "disabled":
			FCGlobals.AktTemp = 0
			FCGlobals.AktVLT = 0
			FCGlobals.AktPWM = 0
			FCGlobals.ZielRPM = 0
			FCGlobals.AktRPM = 0
		self["TxtTemp"].setText(_("Temperature C  {temperature:4.1f}").format(temperature=FCGlobals.AktTemp))
		self["TxtZielRPM"].setText(_("Target rpm  {rpm:4d}").format(rpm=int(FCGlobals.ZielRPM)))
		self["TxtRPM"].setText(_("Current rpm  {rpm:4d}").format(rpm=FCGlobals.AktRPM))
		self["TxtVLT"].setText(_("Voltage  {voltage:03d}").format(voltage=FCGlobals.AktVLT))
		self["TxtPWM"].setText(_("PWM  {pwm:03d}").format(pwm=FCGlobals.AktPWM))
		self["PixTemp"].value = int((FCGlobals.AktTemp - config.plugins.FanControl.temp.value) * 100 / Test0(config.plugins.FanControl.tempmax.value - config.plugins.FanControl.temp.value))
		self["PixZielRPM"].value = int((FCGlobals.ZielRPM - config.plugins.FanControl.minRPM.value) * 100 / Test0(config.plugins.FanControl.maxRPM.value - config.plugins.FanControl.minRPM.value))
		self["PixRPM"].value = int((FCGlobals.AktRPM - config.plugins.FanControl.minRPM.value) * 100 / Test0(config.plugins.FanControl.maxRPM.value - config.plugins.FanControl.minRPM.value))
		self["PixVLT"].value = int(FCGlobals.AktVLT / 2.55)
		self["PixPWM"].value = int(FCGlobals.AktPWM / 2.55)
		if config.plugins.FanControl.Fan.value == "4pinREG":
			if int(abs(FCGlobals.ErrRPM)) <= 10 and FCGlobals.ErrRPM != 0:
				self["PixERR"].value = int(abs(FCGlobals.ErrRPM) * 10)
				self["T10ERR"].setText("10%")
			else:
				self["PixERR"].value = int(abs(FCGlobals.ErrRPM))
				self["T10ERR"].setText("")
			self["TxtERR"].setText(_("PID Ctl Err {error:03.2f} %").format(error=FCGlobals.ErrRPM))
		else:
			self["TxtERR"].setText("")
		self.fan_timer.start(2000, True)

	def pruefen(self):
		self.session.open(FanControl2Test)

	def monitor(self):
		self.session.open(FanControl2Monitor)

	def help(self):
		self.session.open(Console, _("Information"), [f"cat /usr/lib/enigma2/python/Plugins/Extensions/FanControl2/{_('readme.txt')}"])

	def SetupMenu(self):
		self.session.open(FanControl2SpezialSetup)


def DeleteData():
	if config.plugins.FanControl.DeleteData.value == "0" or config.plugins.FanControl.EnableDataLog.value is False:
		return
	try:
		FClog("Auto-Delete Data")
		data_path = f"{config.plugins.FanControl.LogPath.value}FC2data.csv"
		tmp_path = f"{data_path}.tmp"
		with open(data_path, "a") as f:
			s = f.tell()
		if s < 150:
			return
		with open(data_path) as f:
			f.seek(s - 100)
			f.readline()
			line = f.readline()
			DT = line.split(";")
			DT = DT[0].split(" ")
			DD = DT[0].split(".")
			DD48h = date(int(DD[0]), int(DD[1]), int(DD[2])) - timedelta(int(config.plugins.FanControl.DeleteData.value))
			Dfind = f"{DD48h.year:04d}.{DD48h.month:02d}.{DD48h.day:02d} {DT[1]}"
			f.seek(0)
			f.readline()
			with open(tmp_path, "w") as fw:
				fw.write(HeadLine)
				for line in f.readlines():
					DT = line.split(";")
					if DT[0] > Dfind:
						fw.write(line)
		if exists(data_path):
			remove(data_path)
		rename(tmp_path, data_path)
	except Exception:
		FClog("Error Delete Data")


def getstatusoutput(cmd):
	try:
		result = run(f"{{ {cmd}; }}", shell=True, stdout=PIPE, stderr=STDOUT, text=True, check=False)
		return result.returncode, result.stdout.removesuffix("\n")
	except OSError:
		sts = 1
		text = ""
		FClog("Error on call OS program (smartctl/hdparm)")
		return sts, text


def HDDtestTemp():
	if harddiskmanager.HDDCount() > 0 and config.plugins.FanControl.CheckHDDTemp.value != "never":
		FCGlobals.disableHDDread = False
		for hdd in harddiskmanager.HDDList():
			if hdd[1].model().startswith("ATA"):
				FClog(f"{hdd[1].model()} {hdd[1].getDeviceName()} Mode:{config.plugins.FanControl.CheckHDDTemp.value}")
				if config.plugins.FanControl.CheckHDDTemp.value == "auto":
					(stat, wert) = getstatusoutput(f"hdparm -y {hdd[1].getDeviceName()}")
					sleep(0.5)
					(stat, wert) = ReadHDDtemp(hdd[1].getDeviceName())
					if stat != 0:
						(stat, wert) = getstatusoutput(f"smartctl --smart=on {hdd[1].getDeviceName()}")
						FClog("HDD Temperature not readable -> Ignore")
						FCGlobals.FC2HDDignore.append(hdd[1].getDeviceName())
					sleep(0.5)
					(stat, wert) = getstatusoutput(f"hdparm -C {hdd[1].getDeviceName()}")
					if wert.find("standby") > 0:
						FClog("HDD supports Temp reading without Spinup")
					else:
						if hdd[1].isSleeping():
							(stat, wert) = getstatusoutput(f"hdparm -y {hdd[1].getDeviceName()}")
							FClog("HDD not supports Temp reading without Spinup -> Ignore")
							FCGlobals.FC2HDDignore.append(hdd[1].getDeviceName())


def ReadHDDtemp(D):
	return getstatusoutput(f'smartctl -A {D} | grep "194 Temp" | grep Always')


def GetHDDtemp(OneTime):
	FCGlobals.AktHDD = []
	if harddiskmanager.HDDCount() > 0 and config.plugins.FanControl.CheckHDDTemp.value != "never" or OneTime is True:
		for hdd in harddiskmanager.HDDList():
			if hdd[1].model().startswith("ATA") and hdd[1].getDeviceName() not in FCGlobals.FC2HDDignore:
				sleeptime = int((time() - hdd[1].last_access))
#				FClog(f"HDD Temp reading {config.plugins.FanControl.CheckHDDTemp.value} {FCGlobals.disableHDDread} {sleeptime:d}s {hdd[1].isSleeping()}")
				if config.plugins.FanControl.CheckHDDTemp.value == "true" or (config.plugins.FanControl.CheckHDDTemp.value == "auto" and not FCGlobals.disableHDDread) or ((not hdd[1].isSleeping()) and sleeptime < 120) or OneTime is True:
					(stat, wert) = ReadHDDtemp(hdd[1].getDeviceName())
					if stat == 0:
						try:
							FCGlobals.AktHDD.append(int(wert[wert.find("Always") + 6:].replace(" ", "").replace("-", "")[:2]))
						except Exception:
							FCGlobals.AktHDD.append(0)
					if len(FCGlobals.AktHDD) == 0:
						FCGlobals.AktHDD = [0]
					FClog(f"HDD Temp {FCGlobals.AktHDD[-1]:d}C")
	if len(FCGlobals.AktHDD) == 0:
		FCGlobals.AktHDD = [0]


def HDDsSleeping():
	for hdd in harddiskmanager.HDDList():
		if hdd[1].model().startswith("ATA"):
			if not hdd[1].isSleeping():
				return False
	return True


def FC2systemStatus():
	S = int(FCGlobals.FC2werte[5])
	R = " -" if S > 0 else " "
	if (S & 1) > 0:
		R += " BoxOn"
	if (S & 2) > 0:
		R += " HDDon"
	if (S & 4) > 0:
		R += " REC"
	return R


def FC2fanReset():
	setVoltage(id, FCGlobals.AktVLT)
	setPWM(id, FCGlobals.AktPWM)
	FClog("Fan Reset")


class FC2Worker(Thread):
	def __init__(self, index, s, session):
		Thread.__init__(self)
		self.index = index
		self.session = session
		self.s = s

	def run(self):
		while True:
#			print "worker a", self.index
			zahl = FCGlobals.Briefkasten.get()
			if zahl == 1:
				self.s.queryRun()

			FCGlobals.Briefkasten.task_done()


class FanControl2(Screen):
	skin = """ <screen position="100,100" size="300,300" title="FanControl2" > </screen>"""
	RPMController = ControllerPI("RPMController")

	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.FanMin = 500
		self.FanMax = 1500
		self.targetTemp = 50.0
		self.maxTemp = 55.0
		self.Range = 5
		self.Fan = "aus"
		self.dontshutdown = False
		self.inStandby = False
		self.HDDidle = True
		# RPM PI controller initialization - later
		self.RPMController.timer_delay = 10.0
		self.RPMController.dt = 10.0
		self.RPMController.inputMax = 4000.0
		self.RPMController.inputDeadband = 1.0
		self.RPMController.coeffKp = 0.1
		self.RPMController.coeffKi = 0.25
		FClog("Starting up")
		if exists("/usr/lib/enigma2/python/Plugins/Extensions/FanControl2/data/diagram.class.org"):
			rename("/usr/lib/enigma2/python/Plugins/Extensions/FanControl2/data/diagram.class.org", "/usr/lib/enigma2/python/Plugins/Extensions/FanControl2/data/diagram.class")
# 		if not isDMMdisabled() and config.plugins.FanControl.DisableDMM.value:
# 			disableDMM()
		HDDtestTemp()
		GetHDDtemp(False)
		DeleteData()
		FC2threads = [FC2Worker(i, self, session) for i in range(3)]
		for thread in FC2threads:
			thread.daemon = True
			thread.start()
		self.timer = eTimer()
		if self.query not in self.timer.callback:
			self.timer.callback.append(self.query)
		self.timer.startLongTimer(10)
		config.misc.standbyCounter.addNotifier(self.standbyQuery, initial_call=False)

	def FC2AskShutdown(self):
		if not self.dontshutdown:
			self.dontshutdown = True
			self.session.openWithCallback(self.FC2DoShutdown, MessageBox, _("FanControl2 emergency, Box Shutdown now?"), type=MessageBox.TYPE_YESNO, timeout=60)

	def FC2DoShutdown(self, retval):
		if (retval):
			if Standby.inTryQuitMainloop is False:
				self.session.open(Standby.TryQuitMainloop, 1)

	def stop(self):
		FClog("Stop")
		if self.query in self.timer.callback:
			self.timer.callback.remove(self.query)
		self.timer.stop()

	def CurrTemp(self):
		m1 = 0.1
		m2 = 0.1
		ti = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
		templist = FCGlobals.sensors.getSensorsList(FCGlobals.sensors.TYPE_TEMPERATURE)
		tempcount = len(templist)
		for count in range(tempcount):
			tt = FCGlobals.sensors.getSensorValue(count)
			ti[count] = tt
			if m1 < tt:
				mi = count
				m1 = tt
		for count in range(tempcount):
			if m2 < ti[count] and count != mi:
				m2 = ti[count]
		if m2 == 0.1:
			m2 = m1
		return (m1 + m2) / 2.0

	def cycle(self):
		self.Range = self.maxTemp - self.targetTemp
		x = FCGlobals.AktTemp - self.targetTemp
		rpm = skal(x, 0, self.Range, self.FanMin, self.FanMax)
		return rpm

	def standbyQuery(self, configElement):
		Standby.inStandby.onClose.append(self.query)
		self.query()

	def query(self):
		self.timer.stop()
		if config.plugins.FanControl.Fan.value != "disabled":
			FCGlobals.Recording = self.session.nav.RecordTimer.isRecording()
			self.inStandby = Standby.inStandby
			if harddiskmanager.HDDCount() > 0 and int(strftime("%S")) < 10:
				self.HDDidle = HDDsSleeping()
				if strftime("%M")[-1:] == "0":
					GetHDDtemp(False)
			if config.plugins.FanControl.EnableThread.value is True:
				if FCGlobals.Briefkasten.qsize() <= 3:
					FCGlobals.Briefkasten.put(1)
				else:
					FClog("Queue full, Thread hanging?")
			else:
				self.queryRun()
			if FCGlobals.ZielRPM > 0 and FCGlobals.AktRPM == 0:
				FCGlobals.FanFehler += 1
				if FCGlobals.FanFehler > 90:
					FCGlobals.FanFehler -= 18
					FClog("Fan Error")
					if config.plugins.FanControl.ShowError.value == "true" and not self.inStandby:
						AddNotification(MessageBox, _("Fan is not working!"), type=MessageBox.TYPE_INFO, timeout=5)
					if config.plugins.FanControl.ShowError.value == "shutdown":
						self.FC2AskShutdown()
			else:
				FCGlobals.FanFehler = 0
			if FCGlobals.AktTemp >= config.plugins.FanControl.ShutdownTemp.value:
				FClog(f"Emergency Shutdown {int(FCGlobals.AktTemp):d}C")
				self.FC2AskShutdown()
		self.timer.startLongTimer(10)

	def queryRun(self):
		tt = time()
		try:
			if self.targetTemp != config.plugins.FanControl.temp.value:
				self.RPMController.ResetIntegrator()
			self.targetTemp = config.plugins.FanControl.temp.value
			self.maxTemp = config.plugins.FanControl.tempmax.value
			self.Fan = config.plugins.FanControl.Fan.value
			self.Vlt = config.plugins.FanControl.vlt.value
			id = 0
			AktRPMtmp = 0
			# sleeptime = 0
			FCGlobals.AktTemp = self.CurrTemp()
			if int(strftime("%S")) < 10 and strftime("%H:%M") == "00:00":
				DeleteData()
			S = 0
			if not self.inStandby:
				S += 1
			if not self.HDDidle:
				S += 2
			if FCGlobals.Recording:
				S += 4
			FCGlobals.FC2werte[5] = str(S)
			if (self.inStandby) and (not FCGlobals.Overheat) and ((config.plugins.FanControl.StandbyOff.value == "true") or ((config.plugins.FanControl.StandbyOff.value == "trueRec") and (not FCGlobals.Recording and self.HDDidle))):
				FClog(f"Fan Off Temp: {int(FCGlobals.AktTemp):d} {FC2systemStatus()}")
				setVoltage(id, 0)
				setPWM(id, 0)
				FCGlobals.FC2werte[0] = FCGlobals.AktTemp
				FCGlobals.FC2werte[1] = 0
				FCGlobals.FC2werte[2] = 0
				FCGlobals.FC2werte[3] = 0
#				FCGlobals.FC2werte[4] = str(FCGlobals.AktHDD)[1:-1].replace(",","")
				FCGlobals.FC2werte[4] = max(FCGlobals.AktHDD) if len(FCGlobals.AktHDD) > 0 else 0
				FCdata()
				FCGlobals.FirstStart = True
				OverheatTemp = self.maxTemp + config.plugins.FanControl.AddOverheat.value
				FCGlobals.OverheatTimer = 0
				FCGlobals.FanOffWait = True
				if OverheatTemp > 65:
					OverheatTemp = 65
				if FCGlobals.AktTemp > OverheatTemp:
					FCGlobals.Overheat = True
					FClog("Overheat")
			else:
				if (FCGlobals.Overheat and FCGlobals.AktTemp < self.maxTemp - 3) or not self.inStandby:
					FCGlobals.Overheat = False
				AktVLTtmp = getVoltage(id)
				AktPWMtmp = getPWM(id)
				if self.inStandby and self.inStandby == FCGlobals.istStandbySave and FCGlobals.RPMdiff == 1 and not FCGlobals.Recording:
					tmp = GetFanRPM()
					FCGlobals.RPMdiff = FCGlobals.AktRPM - tmp
					if FCGlobals.RPMdiff < 150 or tmp < 300 or self.Fan == "3pin":
						FCGlobals.RPMdiff = 0
					else:
						if config.plugins.FanControl.minRPM.value - FCGlobals.RPMdiff < 300:
							FCGlobals.RPMdiff = config.plugins.FanControl.minRPM.value - 300
						FClog(f"RPM-Range shifted -{FCGlobals.RPMdiff:d}rpm")
				if not self.inStandby:
					FCGlobals.RPMdiff = 0
				self.FanMin = config.plugins.FanControl.minRPM.value - FCGlobals.RPMdiff
				self.FanMax = config.plugins.FanControl.maxRPM.value - FCGlobals.RPMdiff
				if self.inStandby != FCGlobals.istStandbySave or FCGlobals.AktVLT != AktVLTtmp or FCGlobals.AktPWM != AktPWMtmp:
					FCGlobals.istStandbySave = self.inStandby
					if FCGlobals.istStandbySave is True:
						Standby.inStandby.onClose.append(FC2fanReset)
					FC2fanReset()
					AktVLTtmp = FCGlobals.AktVLT
					FCGlobals.RPMdiff = 1
					AktVLTtmp = getVoltage(id)
					AktPWMtmp = getPWM(id)
					if FCGlobals.AktVLT != AktVLTtmp or FCGlobals.AktPWM != AktPWMtmp:
						sleep(2)
						FC2fanReset()
				if (FCGlobals.AktVLT + FCGlobals.AktPWM) == 0:
					FCGlobals.FirstStart = True
				if FCGlobals.FirstStart is True:
					FCGlobals.FirstStart = False
					AktVLTtmp = self.Vlt
					setVoltage(id, self.Vlt)
					setPWM(id, config.plugins.FanControl.pwm.value)
				AktRPMtmp = GetFanRPM()
				if FCGlobals.RPMread > 0 and FCGlobals.RPMread < 3:
					FClog("Reread")
					if config.plugins.FanControl.EnableThread.value is True:
						if FCGlobals.Briefkasten.qsize() <= 2:
							sleep(0.4)
							FCGlobals.Briefkasten.put(1)
					else:
						self.timer.start(400, True)
					return
				FCGlobals.RPMread = 0
				if AktRPMtmp > 6000:
					FClog("ignore high RPM")
					return
				FCGlobals.AktRPM = AktRPMtmp
				FCGlobals.AktVLT = AktVLTtmp
				FCGlobals.AktPWM = getPWM(id)
				if FCGlobals.AktVLT > 255:
					FCGlobals.AktVLT = 255
				FClog(f"Vlt:{FCGlobals.AktVLT:d} Pwm:{FCGlobals.AktPWM:d} Fan:{self.Fan} Pid:{FCGlobals.ErrRPM:.2f}%  {FC2systemStatus()}")
				FCGlobals.FC2werte[0] = FCGlobals.AktTemp
				FCGlobals.FC2werte[1] = FCGlobals.AktRPM
				FCGlobals.FC2werte[2] = FCGlobals.AktVLT
				FCGlobals.FC2werte[3] = FCGlobals.AktPWM
				FCGlobals.FC2werte[4] = max(FCGlobals.AktHDD) if len(FCGlobals.AktHDD) > 0 else 0
				FCdata()
				if int(strftime("%M")) == 0:
					FCGlobals.FC2stunde[int(strftime("%H"))] = f"{FCGlobals.AktTemp:4.1f}<BR>{FCGlobals.AktRPM:d}"
				FCGlobals.ZielRPM = self.cycle()
				if (FCGlobals.FanOffWait and FCGlobals.OverheatTimer < 30) or (FCGlobals.Overheat and FCGlobals.OverheatTimer < 60):
					FCGlobals.ZielRPM = self.FanMin
					FCGlobals.OverheatTimer += 1
					FClog(f"FanStartTimeout set MinRPM ({FCGlobals.OverheatTimer:d})")
				else:
					FCGlobals.FanOffWait = False
				FClog(_("currentRPM:{current:d} targetRPM:{target:d} Temp:{temperature:4.1f}").format(current=FCGlobals.AktRPM, target=int(FCGlobals.ZielRPM), temperature=FCGlobals.AktTemp))
				if self.Fan == "4pin":
					if FCGlobals.AktPWM < 255 and FCGlobals.AktPWM > 0 and FCGlobals.AktVLT != self.Vlt:
						FCGlobals.AktVLT = (FCGlobals.AktVLT - 1 if FCGlobals.AktVLT > self.Vlt else FCGlobals.AktVLT + 1)
						setVoltage(id, FCGlobals.AktVLT)
					if FCGlobals.AktRPM + 29 < FCGlobals.ZielRPM:
						FCGlobals.AktPWM = (FCGlobals.AktPWM + 5 if FCGlobals.ZielRPM - FCGlobals.AktRPM > 100 else FCGlobals.AktPWM + 1)
						setPWM(id, FCGlobals.AktPWM)
						if FCGlobals.AktPWM >= 255 and FCGlobals.AktVLT < 255:
							FCGlobals.AktVLT += 1
							setVoltage(id, FCGlobals.AktVLT)
					elif FCGlobals.AktRPM - 19 > FCGlobals.ZielRPM:
						FCGlobals.AktPWM = (FCGlobals.AktPWM - 5 if FCGlobals.AktRPM - FCGlobals.ZielRPM > 100 else FCGlobals.AktPWM - 1)
						setPWM(id, FCGlobals.AktPWM)
# 4
						if FCGlobals.AktPWM < 0 and FCGlobals.AktVLT > 5:
							FCGlobals.AktVLT -= 1
							setVoltage(id, FCGlobals.AktVLT)
					if FCGlobals.AktVLT > self.Vlt:
						FCGlobals.AktPWM = 256
					if FCGlobals.AktPWM < 0:
						FCGlobals.AktPWM = 0
				elif self.Fan == "4pinREG":
					FCGlobals.AktPWM = self.RPMController.ControlLoop(FCGlobals.ZielRPM, FCGlobals.AktRPM)
					FCGlobals.ErrRPM = self.RPMController.inputError
					if FCGlobals.AktPWM > 255.0:
						FCGlobals.AktVLT = 0.12 * (FCGlobals.AktPWM - 255.0) + int(config.plugins.FanControl.vlt.value)
					else:
						FCGlobals.AktVLT = int(config.plugins.FanControl.vlt.value)       # this will set voltage to initial value
					if FCGlobals.AktVLT > 255:
						FCGlobals.AktVLT = 255
					if FCGlobals.AktVLT < 0:
						FCGlobals.AktVLT = 0
					if FCGlobals.AktPWM > 255:
						FCGlobals.AktPWM = 255
					if FCGlobals.AktPWM < 0:
						FCGlobals.AktPWM = 0
					setVoltage(id, int(FCGlobals.AktVLT))
					setPWM(id, int(FCGlobals.AktPWM))
				elif self.Fan == "3pin":
					if FCGlobals.AktRPM + 29 < FCGlobals.ZielRPM:
						FCGlobals.AktVLT = (FCGlobals.AktVLT + 5 if FCGlobals.ZielRPM - FCGlobals.AktRPM > 100 else FCGlobals.AktVLT + 1)
						setVoltage(id, FCGlobals.AktVLT)
					elif FCGlobals.AktRPM - 19 > FCGlobals.ZielRPM:
						FCGlobals.AktVLT = (FCGlobals.AktVLT - 5 if FCGlobals.AktRPM - FCGlobals.ZielRPM > 100 else FCGlobals.AktVLT - 1)
						setVoltage(id, FCGlobals.AktVLT)
		except Exception:
			FClog(f"Control Error:\n{format_exc()}")
		FClogE(f"Runtime: {time() - tt:.3f}")


def autostart(reason, **kwargs):
	if reason == 0 and "session" in kwargs:
		if exists("/usr/lib/enigma2/python/Plugins/Extensions/WebInterface/__init__.pyo") or exists("/usr/lib/enigma2/python/Plugins/Extensions/WebInterface/__init__.py"):
			from Plugins.Extensions.WebInterface.WebChilds.Toplevel import addExternalChild
			from .FC2webSite import FC2web, FC2webLog, FC2webChart
			from twisted.web import static
			root = static.File("/usr/lib/enigma2/python/Plugins/Extensions/FanControl2/data")
#			root = FC2web()
			root.putChild(b"", FC2web())
			root.putChild(b"log", FC2webLog())
			root.putChild(b"chart", FC2webChart())
			if exists("/usr/lib/enigma2/python/Plugins/Extensions/WebInterface/web/external.xml"):
				try:
					addExternalChild(("fancontrol", root, "Fan Control 2", __version__, True))
					FClog("use new WebIF")
				except Exception:
					addExternalChild(("fancontrol", root))
					FClog("use old WebIF")
			if exists("/usr/lib/enigma2/python/Plugins/Extensions/OpenWebif/pluginshook.src"):
				try:
					addExternalChild(("fancontrol", root, "Fan Control 2", __version__))
					FClog("use new OpenWebIF")
				except Exception:
					pass
		if not exists(f"{FCGlobals.FanPath}/fan_vlt"):
			AddNotification(MessageBox, _("Box has no fancontrol hardware -> FC2 deactivated"), type=MessageBox.TYPE_INFO, timeout=10)
			FClog("not supported, exit")
			return
		session = kwargs["session"]
		session.open(FanControl2)


def selSetup(menuid, **kwargs):
	if FCGlobals.IMAGEDISTRO in ('openhdf'):
		if menuid != "devices_menu":
			return []
	elif FCGlobals.IMAGEDISTRO in ('openatv'):
		if menuid != "extended":
			return []
	else:
		if menuid != "system":
			return []
	return [(_("Fan Control 2"), main, "fansetup_config", 70)]


def Plugins(**kwargs):
	name = _("Fan Control")
	name2 = _("Fan Control 2")
	list = [
	PluginDescriptor(name=name2, description=name, where=[PluginDescriptor.WHERE_SESSIONSTART, PluginDescriptor.WHERE_AUTOSTART], needsRestart=True, fnc=autostart)]
	if exists(f"{FCGlobals.FanPath}/fan_vlt"):
		list.append(PluginDescriptor(name=name2, description=_("setup Fancontol inStandby mode"), where=PluginDescriptor.WHERE_MENU, needsRestart=True, fnc=selSetup))
		if config.plugins.FanControl.FanControlInExtension.value:
			list.append(PluginDescriptor(name=name2, description=name, where=PluginDescriptor.WHERE_EXTENSIONSMENU, icon="plugin.png", needsRestart=True, fnc=main))
		if config.plugins.FanControl.MonitorInExtension.value:
			list.append(PluginDescriptor(name=_("Fan Control 2 - Monitor"), description=name, where=PluginDescriptor.WHERE_EXTENSIONSMENU, icon="plugin.png", needsRestart=True, fnc=mainMonitor))
	return list
