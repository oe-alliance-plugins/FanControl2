from datetime import date, timedelta
from os import stat, remove, rename, statvfs
from os.path import exists
from twisted.web import resource, http
from Components.config import config
from .__init__ import _, __version__, HeadLine, TempName
from .globals import FCGlobals
from .plugin import Free
from .Sensors import sensors

setattr(FCGlobals, "sensors", sensors)

########################################################

SIGN = "°"
TITLE = "FanControl2 Webinterface"


def _get_arg(req, key):
	value = req.args.get(key.encode("utf-8"))
	if value is None:
		value = req.args.get(key)
	if not value:
		return None
	first = value[0] if isinstance(value, (list, tuple)) else value
	if isinstance(first, bytes):
		return first.decode("utf-8", "ignore")
	return first


def _html_response(req, html):
	if isinstance(html, str):
		return html.encode("utf-8")
	return html


def get_head(refresh, title):
	html = "<html>"
	html += "<head>\n"
	html += "<meta http-equiv=\"Content-Language\" content=\"de\">\n"
	html += "<meta http-equiv=\"Content-Type\" content=\"text/html; charset=UTF-8\">\n"
	html += "<meta http-equiv=\"cache-control\" content=\"no-cache\" />\n"
	html += "<meta http-equiv=\"pragma\" content=\"no-cache\" />\n"
	html += "<meta http-equiv=\"expires\" content=\"0\">\n"
	if refresh:
		html += "<meta http-equiv=\"refresh\" content=\"20\">\n"
	html += f"<title>Fan Control 2 - {title}</title>\n"
	html += "</head>"
	html += "<body bgcolor=\"#666666\" text=\"#FFFFFF\">\n"
	return html


class FC2web(resource.Resource):

	title = TITLE
	isLeaf = False

	def render(self, req):
		req.setHeader('Content-type', 'text/html; charset=UTF-8')

		""" rendering server response """
		#command = _get_arg(req, "cmd")

		html = get_head(True, "Info")
		html += "<form method=\"POST\" action=\"--WEBBOT-SELF--\">\n"
		html += "<table border=\"1\" width=\"500\" bordercolorlight=\"#000000\" bordercolordark=\"#000000\" cellspacing=\"1\"><tr><td bgcolor=\"#000000\" width=\"200\">\n"
		html += "<p align=\"center\"><img border=\"0\" src=\"/fancontrol/FC2dreambox.png\" width=\"181\" height=\"10\">\n"
		html += "<font color=\"#FFFFFF\"><BR><b>Fan Control 2 - Info</b></font></p>\n"
		html += "</td><td bgcolor=\"#000000\">\n"
		html += "<p align=\"right\">"
		html += BoxStatus()
		if exists(config.plugins.FanControl.LogPath.value + "FC2data.csv"):
			html += "<a href=\"/fancontrol/chart\"><img border=\"0\" src=\"/fancontrol/FC2Chart.png\" width=\"100\" height=\"40\"></a>\n"
		html += "<a href=\"/fancontrol/log\"><img border=\"0\" src=\"/fancontrol/FC2Setup.png\" width=\"100\" height=\"40\"></a></td></tr></table>\n"
		html += "<table border=\"1\" width=\"500\" id=\"table1\">\n"
		html += "<tr>\n"
		html += f"<td>{_('Temperature')}: <b><font color=\"#FFCC00\">{FCGlobals.FC2werte[0]:4.1f} {SIGN}C</font></b></td>\n"
		html += f"<td>{_('Speed')}: <font color=\"#FFCC00\"><b>{FCGlobals.FC2werte[1]:4d} rpm</b></font></td>\n"
		html += f"<td>{_('Voltage')}: <font color=\"#FFCC00\"><b>{FCGlobals.FC2werte[2]:03d}</b></font></td>\n"
		html += f"<td>PWM: <font color=\"#FFCC00\"><b>{FCGlobals.FC2werte[3]:03d}</b></font></td>\n"
		html += "</tr>\n"
		html += "</table>\n"

		html += "<table border=\"1\" width=\"500\">\n"
		html += "<tr>\n"
		html += f"<td>{SIGN} {_('Sensors')}C</td>\n"
		templist = FCGlobals.sensors.getSensorsList(FCGlobals.sensors.TYPE_TEMPERATURE)
		tempcount = len(templist)
		for count in range(tempcount):
			if FCGlobals.sensors.getSensorName(count) == "undefined":
				N = TempName[count]
			else:
				N = FCGlobals.sensors.getSensorName(count)
			html += f"<td><font color=\"#FFCC00\" title=\"{N}\">{FCGlobals.sensors.getSensorValue(count):d}</font></td>"
		if FCGlobals.FC2werte[4] > 0:
			html += f"<td><font size=\"1\">HDD </font><font color=\"#FFCC00\">{FCGlobals.FC2werte[4]:d}</font></td>\n"
		html += "</tr>\n"
		html += "</table>\n"

		html += "<table border=\"1\" width=\"500\">\n"
		html += "<tr>\n"
		for count in range(0, 12):
			tmp = ("<BR>-" if FCGlobals.FC2stunde[count] == "-" else FCGlobals.FC2stunde[count])
			html += f"<td><p align=\"center\"><font size=\"1\">{count:02d}:00<br><font color=\"#FFCC00\">{tmp}</font></font></td>\n"
		html += "</tr><tr>\n"
		for count in range(12, 24):
			tmp = ("<BR>-" if FCGlobals.FC2stunde[count] == "-" else FCGlobals.FC2stunde[count])
			html += f"<td><p align=\"center\"><font size=\"1\">{count:02d}:00<br><font color=\"#FFCC00\">{tmp}</font></font></td>\n"
		html += "</tr></table>\n"

		html += "<script type=\"text/javascript\">\n"
		html += "function doLogWrite() {\n"
		html += "var iFrameWin = window.myIFrameName;\n"
		html += "iFrameWin.document.write('<html><head><title>FC2 Log Window</title></head><body bgcolor=\"#D3D3D3\">');\n"
		html += "iFrameWin.document.write('<font size=\"-1\">');\n"
		for L in FCGlobals.FC2Log:
			html += "iFrameWin.document.write('" + L + "<br>');\n"
		html += "iFrameWin.document.write('</font>');\n"
		html += "iFrameWin.document.write('</body></html>');\n"
		html += "iFrameWin.document.close();\n"
		html += "}\n"
		html += "</script>\n"
		html += "<iframe id=\"myIFrameId\" name=\"myIFrameName\" width=\"500\" height=\"320\" marginwidth=\"5\" vspace=\"2\" marginheight=\"5\" frameborder=\"1\" scrolling=\"auto\"></iframe>\n"
		html += "<script>doLogWrite();\n"
		html += "myIFrameName.document.body.scrollTop = myIFrameName.document.body.scrollHeight*100;\n"
		html += "</script>\n"

		html += "<table border=\"1\" width=\"500\">\n"
		html += "<tr>\n"
		html += f"<td>Version: V{__version__} </td>\n"
		html += f"<td>Settings: {config.plugins.FanControl.temp.value}-{config.plugins.FanControl.tempmax.value} {SIGN}C</td>\n"
		html += f"<td>{config.plugins.FanControl.minRPM.value}-{config.plugins.FanControl.maxRPM.value} rpm</td>\n"
		html += "</tr>\n"
		html += "</table>\n"
		html += "</body>\n"
		html += "</html>\n"

		html += "</form>\n"

		return _html_response(req, html)

##########################################################


class FC2webLog(resource.Resource):

	title = TITLE
	isLeaf = True

	def render(self, req):
		command = _get_arg(req, "cmd")
		html = ""
		if command is None:
			req.setHeader('Content-type', 'text/html')

			""" rendering server response """

			html = get_head(True, "Logging")
			html += "<table border=\"1\" width=\"500\" bordercolorlight=\"#000000\" bordercolordark=\"#000000\" cellspacing=\"1\"><tr><td bgcolor=\"#000000\" width=\"200\">\n"
			html += "<p align=\"center\"><img border=\"0\" src=\"/fancontrol/FC2dreambox.png\" width=\"181\" height=\"10\">\n"
			html += "<font color=\"#FFFFFF\"><BR><b>Fan Control 2 - Logging</b></font></p>\n"
			html += "</td><td bgcolor=\"#000000\">\n"
			html += "<p align=\"right\">"
			html += BoxStatus()
			if exists(config.plugins.FanControl.LogPath.value + "FC2data.csv"):
				html += "<a href=\"/fancontrol/chart\"><img border=\"0\" src=\"/fancontrol/FC2Chart.png\" width=\"100\" height=\"40\"></a>\n"
			html += "<a href=\"/fancontrol\"><img border=\"0\" src=\"/fancontrol/FC2Info.png\" width=\"100\" height=\"40\"></a></td></tr></table>\n"

			html += "<table border=\"1\" width=\"500\">"
			html += "<tr><td width=\"50%\" align=\"center\" valign=\"top\">Data Logging "
			if config.plugins.FanControl.EnableDataLog.value:
				html += f"<font color=\"#00FF00\">{_('active')}</font>"
				html += "<form method=\"GET\">"
				html += "<input type=\"hidden\" name=\"cmd\" value=\"dataenable\">"
				html += f"<input type=\"submit\" value=\"{_('turn off')}\">"
				html += "</form>"
			else:
				html += f"<font color=\"#FF0000\">{_('not active')}</font>"
				html += "<form method=\"GET\">"
				html += "<input type=\"hidden\" name=\"cmd\" value=\"dataenable\">"
				html += f"<input type=\"submit\" value=\"{_('turn on')}\">"
				html += "</form>"
			if exists(config.plugins.FanControl.LogPath.value + "FC2data.csv"):
				s = stat(config.plugins.FanControl.LogPath.value + "FC2data.csv")
				if int(s.st_size / 1024) == 0:
					html += "<BR>" + _("Filesize : {size:d} {unit}Byte").format(size=int(s.st_size), unit="")
				else:
					html += "<BR>" + _("Filesize : {size:d} {unit}Byte").format(size=int(s.st_size / 1024), unit="k")
				s = statvfs(config.plugins.FanControl.LogPath.value)
				html += "<BR>" + _("Disk free : {size:d} MByte").format(size=int(s.f_bsize * s.f_bavail / 1024 / 1024))
				html += "<form method=\"GET\">"
				html += "<input type=\"hidden\" name=\"cmd\" value=\"data\">"
				html += f"<input type=\"submit\" value=\"{_('Download')}\">"
				html += "</form>"
				html += "<form method=\"GET\">"
				html += "<input type=\"hidden\" name=\"cmd\" value=\"datadel\">"
				html += f"<input type=\"submit\" value=\"{_('Delete')}\">"
				html += "</form>"
				html += "<form method=\"GET\">"
				html += "<input type=\"hidden\" name=\"cmd\" value=\"datadel48h\">"
				html += f"<input type=\"submit\" value=\"{_('Delete older 48h')}\">"
				html += "</form>"
			else:
				html += "<BR>" + _("File {filename} does not exists").format(filename="FC2data.csv")

			html += "</td><td width=\"50%\" align=\"center\" valign=\"top\">Event Logging "
			if config.plugins.FanControl.EnableEventLog.value:
				html += f"<font color=\"#00FF00\">{_('active')}</font>"
				html += "<form method=\"GET\">"
				html += "<input type=\"hidden\" name=\"cmd\" value=\"eventsenable\">"
				html += f"<input type=\"submit\" value=\"{_('turn off')}\">"
				html += "</form>"
			else:
				html += f"<font color=\"#FF0000\">{_('not active')}</font>"
				html += "<form method=\"GET\">"
				html += "<input type=\"hidden\" name=\"cmd\" value=\"eventsenable\">"
				html += f"<input type=\"submit\" value=\"{_('turn on')}\">"
				html += "</form>"
			if exists(config.plugins.FanControl.LogPath.value + "FC2events.txt"):
				s = stat(config.plugins.FanControl.LogPath.value + "FC2events.txt")
				if int(s.st_size / 1024) == 0:
					html += "<BR>" + _("Filesize : {size:d} {unit}Byte").format(size=int(s.st_size), unit="")
				else:
					html += "<BR>" + _("Filesize : {size:d} {unit}Byte").format(size=int(s.st_size / 1024), unit="k")
				s = statvfs(config.plugins.FanControl.LogPath.value)
				html += "<BR>" + _("Disk free : {size:d} MByte").format(size=int(s.f_bsize * s.f_bavail / 1024 / 1024))
				html += "<form method=\"GET\">"
				html += "<input type=\"hidden\" name=\"cmd\" value=\"events\">"
				html += f"<input type=\"submit\" value=\"{_('Download')}\">"
				html += "</form>"
				html += "<form method=\"GET\">"
				html += "<input type=\"hidden\" name=\"cmd\" value=\"eventsdel\">"
				html += f"<input type=\"submit\" value=\"{_('Delete')}\">"
				html += "</form>"
#				html += "<form method=\"GET\">"
#				html += "<input type=\"hidden\" name=\"cmd\" value=\"eventsdel48h\">"
#				html += f"<input type=\"submit\" value=\"{_('Delete older 48h')}\">"
#				html += "</form>"

			else:
				html += "<BR>" + _("File {filename} does not exists").format(filename="FC2events.txt")
			html += "</td></tr></table>"
			html += _("Logging-Path: {path}").format(path=config.plugins.FanControl.LogPath.value)
			html += "<BR>" + _("Auto-Delete older {days} Days").format(days=config.plugins.FanControl.DeleteData.value)
			html += "</html>"

		elif command[0] == "data":
			req.setResponseCode(http.OK)
#			req.setHeader('Content-type', 'application/octet-stream')
			req.setHeader('Content-type', 'application/vnd.ms-excel')
			req.setHeader('Content-Disposition', 'attachment;filename=FC2data.csv')
			req.setHeader('Content-Length', stat(config.plugins.FanControl.LogPath.value + "FC2data.csv").st_size)
#			req.setHeader('Content-Disposition', 'inline;filename=FC2data.csv')
			with open(config.plugins.FanControl.LogPath.value + "FC2data.csv") as f:
				html = f.read()
		elif command[0] == "datadel":
			if exists(config.plugins.FanControl.LogPath.value + "FC2data.csv"):
				remove(config.plugins.FanControl.LogPath.value + "FC2data.csv")
			CreateDataHead()
			html = LogRefresh()
		elif command[0] == "datadel48h":
			if exists(config.plugins.FanControl.LogPath.value + "FC2data.csv") and stat(config.plugins.FanControl.LogPath.value + "FC2data.csv").st_size > 10000:
				with open(config.plugins.FanControl.LogPath.value + "FC2data.csv", "a") as f:
					s = f.tell()
				with open(config.plugins.FanControl.LogPath.value + "FC2data.csv") as f:
					f.seek(s - 100)
					line = f.readline()
					line = f.readline()
					DT = line.split(";")
					DT = DT[0].split(" ")
					DD = DT[0].split(".")
					DD48h = date(int(DD[0]), int(DD[1]), int(DD[2])) - timedelta(2)
					Dfind = f"{DD48h.year:04d}.{DD48h.month:02d}.{DD48h.day:02d} {DT[1]}"
					f.seek(0)
					line = f.readline()
					with open(config.plugins.FanControl.LogPath.value + "FC2data.csv.tmp", "w") as fw:
						fw.write(HeadLine)
						for line in f.readlines():
							DT = line.split(";")
							if DT[0] > Dfind:
								fw.write(line)
				if exists(config.plugins.FanControl.LogPath.value + "FC2data.csv"):
					remove(config.plugins.FanControl.LogPath.value + "FC2data.csv")
				if exists(config.plugins.FanControl.LogPath.value + "FC2data.csv.tmp"):
					rename(config.plugins.FanControl.LogPath.value + "FC2data.csv.tmp", config.plugins.FanControl.LogPath.value + "FC2data.csv")
			html = LogRefresh()
		elif command[0] == "dataenable":
			config.plugins.FanControl.EnableDataLog.value = not config.plugins.FanControl.EnableDataLog.value
			CreateDataHead()
			config.plugins.FanControl.EnableDataLog.save()
			html = LogRefresh()

		elif command[0] == "events":
			req.setResponseCode(http.OK)
			req.setHeader('Content-type', 'application/octet-stream')
			req.setHeader('Content-Disposition', 'attachment;filename=FC2events.txt')
			req.setHeader('Content-Length', stat(config.plugins.FanControl.LogPath.value + "FC2events.txt").st_size)
#			req.setHeader('Content-Disposition', 'inline;filename=FC2events.txt')
			with open(config.plugins.FanControl.LogPath.value + "FC2events.txt") as f:
				html = f.read()
		elif command[0] == "eventsdel":
			if exists(config.plugins.FanControl.LogPath.value + "FC2events.txt"):
				remove(config.plugins.FanControl.LogPath.value + "FC2events.txt")
			html = LogRefresh()
		elif command[0] == "eventsdel48h":
			if exists(config.plugins.FanControl.LogPath.value + "FC2events.txt"):
				with open(config.plugins.FanControl.LogPath.value + "FC2events.txt", "a") as f:
					s = f.tell()
				with open(config.plugins.FanControl.LogPath.value + "FC2events.txt") as f:
					f.seek(s - 100)
					line = f.readline()
					line = f.readline()
					DT = line.split(";")
					DT = DT[0].split(" ")
					DD = DT[0].split(".")
					DD48h = date(int(DD[0]), int(DD[1]), int(DD[2])) - timedelta(2)
					Dfind = f"{DD48h.year:04d}.{DD48h.month:02d}.{DD48h.day:02d} {DT[1]}"
					f.seek(0)
					line = f.readline()
					with open(config.plugins.FanControl.LogPath.value + "FC2events.txt.tmp", "w") as fw:
						fw.write(HeadLine)
						for line in f.readlines():
							DT = line.split(";")
							if DT[0] > Dfind:
								fw.write(line)
				if exists(config.plugins.FanControl.LogPath.value + "FC2events.txt"):
					remove(config.plugins.FanControl.LogPath.value + "FC2events.txt")
				if exists(config.plugins.FanControl.LogPath.value + "FC2events.txt.tmp"):
					rename(config.plugins.FanControl.LogPath.value + "FC2events.txt.tmp", config.plugins.FanControl.LogPath.value + "FC2events.txt")
			html = LogRefresh()
		elif command[0] == "eventsenable":
			config.plugins.FanControl.EnableEventLog.value = not config.plugins.FanControl.EnableEventLog.value
			config.plugins.FanControl.EnableEventLog.save()
			html = LogRefresh()

		return _html_response(req, html)


def LogRefresh():
	h = "<html>"
	h += "<head>"
	h += "<meta http-equiv=\"refresh\" content=\"1; url=/fancontrol/log\">"
	h += "<a href=\"/fancontrol/log\">Execution completed... jump back...</a>"
	h += "</html>"
	h += "</head>"
	return h


def CreateDataHead():
	if not exists(config.plugins.FanControl.LogPath.value + "FC2data.csv") and config.plugins.FanControl.EnableDataLog.value and Free(config.plugins.FanControl.LogPath.value):
		try:
			with open(config.plugins.FanControl.LogPath.value + "FC2data.csv", "w") as f:
				f.write(HeadLine)
		except OSError:
			pass

##########################################################


class FC2webChart(resource.Resource):

	title = TITLE
	isLeaf = True

	def render(self, req):
		# command = _get_arg(req, "cmd")
		html = ""
		if exists(config.plugins.FanControl.LogPath.value + "FC2data.csv"):
			req.setHeader('Content-type', 'text/html')  # rendering server response
			data_path = config.plugins.FanControl.LogPath.value + "FC2data.csv"
			s = stat(data_path).st_size
			if s < 150:
				html = "<html><body><html>Not enough Data (wait 3min)!</body></html>"
				return _html_response(req, html)
			with open(data_path) as f:
				f.seek(s - 100)
				f.readline()
				DT = f.readline().split(";", 1)[0].split(" ")
				DD = DT[0].split(".")
				DD48h = date(int(DD[0]), int(DD[1]), int(DD[2])) - timedelta(2)
				Dfind = f"{DD48h.year:04d}.{DD48h.month:02d}.{DD48h.day:02d} {DT[1]}"
				f.seek(0)
				f.readline()
				lines = f.readlines()
			filtered_lines = [line for line in lines if line.split(";", 1)[0] > Dfind]
			Anzahl = len(filtered_lines)
			DT = filtered_lines[-1].split(";") if filtered_lines else DT
			html = get_head(True, "Chart")
			html += "<table border=\"1\" width=\"900\" bordercolorlight=\"#000000\" bordercolordark=\"#000000\"  cellspacing=\"1\"><tr><td bgcolor=\"#000000\" width=\"200\">\n"
			html += "<p align=\"center\"><img border=\"0\" src=\"/fancontrol/FC2dreambox.png\" width=\"181\" height=\"10\">\n"
			html += "<font color=\"#FFFFFF\"><BR><b>Fan Control 2 - Chart</b></font></p>\n"
			html += "</td><td bgcolor=\"#000000\">\n"
			html += "<p align=\"right\">"
			html += BoxStatus()
			if exists(config.plugins.FanControl.LogPath.value + "FC2data.csv"):
				html += "<a href=\"/fancontrol\"><img border=\"0\" src=\"/fancontrol/FC2Info.png\" width=\"100\" height=\"40\"></a>\n"
			html += "<a href=\"/fancontrol/log\"><img border=\"0\" src=\"/fancontrol/FC2Setup.png\" width=\"100\" height=\"40\"></a></td></tr></table>\n"
			html += "<applet code=\"diagram.class\" codebase=\"/fancontrol/\" name=\"DiaTemp\" "
			html += "align=\"baseline\" width=\"900\" height=\"250\" mayscript>\n"
			html += f"<param name=\"title\" value=\"Temp  (48h - {DT[0]})\">\n"
			html += "<param name=\"bgcolor\" value=\"240; 240; 240\">\n"
			html += "<param name=\"ytitle\" value=\"Temp\">\n"
			html += f"<param name=\"rolling\" value=\"{Anzahl:d}\">\n"
			html += "<param name=\"show_xscale\" value=\"atText\">\n"
			html += "<param name=\"show_ygrid\" value=\"true\">\n"
			html += "<param name=\"show_xgrid\" value=\"true\">\n"
			html += "<param name=\"y0\" value=\"\">\n"
			html += "<param name=\"color0\" value=\"240; 0; 0\">\n"
			html += "<param name=\"style0\" value=\"LINE\">\n"
			html += "<param name=\"ylabel0\" value=\"Temp\">\n"
			html += "<param name=\"y1\" value=\"\">\n"
			html += "<param name=\"color1\" value=\"240; 0; 240\">\n"
			html += "<param name=\"style1\" value=\"LINE\">\n"
			html += "<param name=\"ylabel1\" value=\"HDD\">\n"
			html += "<param name=\"y2\" value=\"\">\n"
			html += "<param name=\"color2\" value=\"0; 255; 0\">\n"
			html += "<param name=\"style2\" value=\"LINE\">\n"
			html += "<param name=\"ylabel2\" value=\"BoxOn\">\n"
			html += "<param name=\"y3\" value=\"\">\n"
			html += "<param name=\"color3\" value=\"72; 118; 255\">\n"
			html += "<param name=\"style3\" value=\"LINE\">\n"
			html += "<param name=\"ylabel3\" value=\"HDDon\">\n"
			html += "<param name=\"y4\" value=\"\">\n"
			html += "<param name=\"color4\" value=\"255; 165; 0\">\n"
			html += "<param name=\"style4\" value=\"LINE\">\n"
			html += "<param name=\"ylabel4\" value=\"Record\">\n"
			html += "</applet>\n"
#			html += "<div style=\"position: absolute; width: 100px; height: 100px; z-index: 1; left: 910px; top: 146px\" id=\"Ebene1\">\n"
#			html += "<img border=\"0\" src=\"/web-data/fc2/FC2Status.png\" width=\"115\" height=\"168\"></div>\n"
			html += "<applet code=\"diagram.class\" codebase=\"/fancontrol/\" name=\"DiaRPM\" "
			html += "align=\"baseline\" width=\"900\" height=\"250\" mayscript>\n"
			html += f"<param name=\"title\" value=\"RPM  (48h - {DT[0]})\">\n"
			html += "<param name=\"bgcolor\" value=\"240; 240; 240\">\n"
			html += "<param name=\"ytitle\" value=\"RPM\">\n"
			html += f"<param name=\"rolling\" value=\"{Anzahl:d}\">\n"
			html += "<param name=\"show_xscale\" value=\"atText\">\n"
			html += "<param name=\"show_ygrid\" value=\"true\">\n"
			html += "<param name=\"show_xgrid\" value=\"true\">\n"
			html += "<param name=\"y0\" value=\"\">\n"
			html += "<param name=\"color0\" value=\"240; 0; 0\">\n"
			html += "<param name=\"style0\" value=\"LINE\">\n"
			html += "<param name=\"ylabel0\" value=\"RPM\">\n"
			html += "</applet>\n"
			html += "<script language=javascript>\n"
			html += "dT = document.DiaTemp\n"
			html += "dR = document.DiaRPM\n"
			t = 0
			Xtime = int(Anzahl / 20)
			if Anzahl < 1000:
				Xtime += 1
			for line in filtered_lines:
				DT = line.split(";")
				if Xtime > 0:
					tmp = ("\"" + DT[0].split(" ")[1] + "\"") if t % Xtime == 0 else "null"
				else:
					tmp = "null"
				t += 1
				if len(DT[6]) > 1:
					DT[6] = "0"
				B = 0
				H = 0
				R = 0
				S = int(DT[6])
				if (S & 1) > 0:
					B = 3
				if (S & 2) > 0:
					H = 6
				if (S & 4) > 0:
					R = 9
				html += f"dT.AddPoint(\"{DT[1].replace(',', '.')}; {DT[5]}; {B:d}; {H:d}; {R:d}\", {tmp}, null);\n"
				html += f"dR.AddPoint(\"{DT[2]}\", {tmp}, null);\n"
			html += "dT.repaint();\ndR.repaint();\n"
			html += "</script>"
		else:
			html = "<html>no Data!"
		html += "</body>"
		html += "</html>"

		return _html_response(req, html)


def BoxStatus():
	h = ""
	S = int(FCGlobals.FC2werte[5])
	if (S & 1) > 0:
		h += "<img border=\"0\" src=\"/fancontrol/FC2on.png\" width=\"20\" height=\"20\" title=\"Box On\" align=\"left\" hspace=\"2\" vspace=\"5\">\n"
	if (S & 2) > 0:
		h += "<img border=\"0\" src=\"/fancontrol/FC2hdd.png\" width=\"20\" height=\"20\" title=\"HDD On\" align=\"left\" hspace=\"2\" vspace=\"5\">\n"
	if (S & 4) > 0:
		h += "<img border=\"0\" src=\"/fancontrol/FC2record.png\" width=\"20\" height=\"20\" title=\"Recording\" align=\"left\" hspace=\"2\" vspace=\"5\">\n"
	return h
