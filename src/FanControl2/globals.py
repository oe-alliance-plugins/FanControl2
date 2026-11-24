from queue import Queue


class FCGlobals:
	IMAGEDISTRO = None
	MACHINE = None
	sensors = None
	Briefkasten = Queue()
	FritzTime = 0
	AktERR = 0
	AktPWMCTL = 0
	FirstStart = True
	FanOffWait = False
	ZielRPM = 0
	OverheatTimer = 0
	IntegralRPM = 0
	AktVLT = 0
	DataMinute = ""
	FC2HDDignore = []
	AktPWM = 0
	AktRPM = 0
	AktTemp = 0
	AktHDD = []
	LastVLT = 0
	LastPWM = 0
	ErrRPM = 0
	FanFehler = 0
	Overheat = False
	Recording = False
	RPMread = 0
	RPMdiff = 0
	RPMrunning = False
	istStandbySave = False
	disableHDDread = False
	FC2Log = []
	FC2werte = [0.1, 0, 0, 0, 0, 0]
	FC2stunde = ["-"] * 24
	FanPath = "/proc/stb/fp"
