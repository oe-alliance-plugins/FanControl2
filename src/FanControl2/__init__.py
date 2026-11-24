from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
from gettext import bindtextdomain, dgettext, gettext

PluginLanguageDomain = "FanControl2"
PluginLanguagePath = "Extensions/FanControl2/locale"


def localeInit():
	bindtextdomain(PluginLanguageDomain, resolveFilename(SCOPE_PLUGINS, PluginLanguagePath))


def _(txt):
	if dgettext(PluginLanguageDomain, txt):
		return dgettext(PluginLanguageDomain, txt)
	else:
		print(f"[{PluginLanguageDomain}] fallback to default translation for {txt}")
		return gettext(txt)


localeInit()
language.addCallback(localeInit)

HeadLine = "Time;Temp;RPM;VLT;PWM;HDD;Status;Temp1;Temp2;Temp3;Temp4;Temp5;Temp6;Temp7;Temp8\r\n"
TempName = [
	_("below Tunerslot 4"),
	_("near XILINX Spartan"),
	_("under the WLAN"),
	_("left of the Battery"),
	_("left near Front-CI"),
	_("left near Card-Slot"),
	_("over Security Card"),
	_("under the Fan")
]


__version__ = "2.9.3"
