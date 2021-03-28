##########################################
## Python module lor logging application##
##                                      ##
## Written by Juanma					##
##########################################
import machine
import sys
import io

CRITICAL = const(50)
ERROR    = const(40)
WARNING  = const(30)
INFO     = const(20)
DEBUG    = const(10)
NOTSET   = const(0)

_level_dict = {
	CRITICAL: "CRITICAL",
	ERROR: "ERROR",
	WARNING: "WARNING",
	INFO: "INFO",
	DEBUG: "DEBUG",
}

class Logger:
	level = NOTSET
	def __init__(self, name):
		#print("New Logger [{}]".format(name))
		self.name = name
		self.handlers = None
	def _level_str(self, level):
		l = _level_dict.get(level)
		if l is not None:
			return l
		return "LVL%s" % level
	def setLevel(self, level):
		self.level = level
	def isEnabledFor(self, level):
		return level >= (self.level or _level)
	def log(self, level, msg, *args):
		if level >= (self.level or _level):
			record = LogRecord(self.name, level, None, None, msg, args, None, None, None)
			if self.handlers:
				for hdlr in self.handlers:
					hdlr.emit(record)
			#else:
				#print("No handlers")
	def debug(self, msg, *args):
		self.log(DEBUG, msg, *args)
	def info(self, msg, *args):
		self.log(INFO, msg, *args)
	def warning(self, msg, *args):
		self.log(WARNING, msg, *args)
	def error(self, msg, *args):
		self.log(ERROR, msg, *args)
	def critical(self, msg, *args):
		self.log(CRITICAL, msg, *args)
	def exc(self, e, msg, *args):
		buf = uio.StringIO()
		sys.print_exception(e, buf)
		self.log(ERROR, msg + "\n" + buf.getvalue(), *args)
	def exception(self, msg, *args):
		self.exc(sys.exc_info()[1], msg, *args)
	def addHandler(self, hdlr):
		if self.handlers is None:
			self.handlers = []
		self.handlers.append(hdlr)
		#print ("Handler added [{}]".format(len(self.handlers)))

_level = INFO
_loggers = {}
_defaultformatter= None

def getLogger(name=None):
	global _defaultformatter, _loggers
	if name is None:
		name = "root"
	if name in _loggers:
		return _loggers[name]
	else:
		l = Logger(name)
		sh = StreamHandler()
		if _defaultformatter:
			sh.formatter = _defaultformatter
		else:
			sh.formatter = Formatter()
		l.addHandler(sh)
		_loggers[name] = l
		return l

def info(msg, *args):
	getLogger(None).info(msg, *args)

def debug(msg, *args):
	logger = getLogger(None)
	logger.debug(msg, *args)

def basicConfig(level=INFO, fmt=None, style="{", filename=None, stream=None):
	global _level, _defaultformatter
	_level = level
	if filename:
		h = FileHandler(filename)
	else:
		h = StreamHandler(stream)
	if fmt:
		_defaultformatter = Formatter(fmt, style=style)
	h.setFormatter(_defaultformatter)
	root.handlers.clear()
	root.addHandler(h)


class Handler:
	def __init__(self):
		self.formatter = Formatter()
	def setFormatter(self, fmt):
		self.formatter = fmt


class StreamHandler(Handler):
	def __init__(self, stream=None):
		self._stream = stream or sys.stderr
		self.terminator = "\n"
		self.formatter = Formatter()
	def emit(self, record):
		#print("Emiting logging record format:[{}]".format(self.formatter.fmt))
		self._stream.write(self.formatter.format(record) + self.terminator)
	def flush(self):
		pass


class FileHandler(Handler):
	def __init__(self, filename, mode="a", encoding=None, delay=False):
		super().__init__()

		self.encoding = encoding
		self.mode = mode
		self.delay = delay
		self.terminator = "\n"
		self.filename = filename
		self._f = None
		if not delay:
			self._f = open(self.filename, self.mode)
	def emit(self, record):
		if self._f is None:
			self._f = open(self.filename, self.mode)
		self._f.write(self.formatter.format(record) + self.terminator)
	def close(self):
		if self._f is not None:
			self._f.close()


class Formatter:
	converter = machine.RTC().datetime
	def __init__(self, fmt=None, datefmt=None, style="{"):
		if style=="%":
			self.fmt = fmt or "%(message)s"
		elif style=="{":
			self.fmt = fmt or "{message}"
		else:
			raise ValueError("Style must be one of: %, {")
		self.style = style
		self.datefmt = datefmt
	def usesTime(self):
		if self.style == "%":
			return "%(asctime)" in self.fmt
		elif self.style == "{":
			return "{asctime" in self.fmt
	def format(self, record):
		# The message attribute of the record is computed using msg % args.
		if self.style == "%":
			record.message = record.msg % record.args
		else:
			try:
				record.message = record.msg.format(*record.args)
			except Exception as e:
				sys.print_exception(e)
				print("record.msg==[{}], record.args==[{}]", record.msg, record.args)
			
		# If the formatting string contains '(asctime)', formatTime() is called to
		# format the event time.
		if self.usesTime():
			record.asctime = self.formatTime(record, self.datefmt)
		# If there is exception information, it is formatted using formatException()
		# and appended to the message. The formatted exception information is cached
		# in attribute exc_text.
		if record.exc_info is not None:
			record.exc_text += self.formatException(record.exc_info)
			record.message += "\n" + record.exc_text
		# The record’s attribute dictionary is used as the operand to a string
		# formatting operation.
		if self.style == "%":
			return self.fmt % record.__dict__
		elif self.style == "{":
			try:
				return self.fmt.format(**record.__dict__)
			except Exception as e:
				sys.print_exception(e)
				print("format request: {}.format(**{})", self.fmt, record.__dict__)
				
		else:
			raise ValueError("Style {0} is not supported by logging.".format(self.style))
	def formatTime(self, record, datefmt=None):
		assert datefmt is None  # datefmt is not supported
		#ct = utime.localtime(record.created)
		#return "{0}-{1}-{2} {4}:{5}:{6}.{7:5.4}".format(*ct)
		return "{0}-{1:02}-{2:02} {4:02}:{5:02}:{6:02}.{7:06}".format(*record.created)
	def formatException(self, exc_info):
		raise NotImplementedError()
	def formatStack(self, stack_info):
		raise NotImplementedError()

root = getLogger()

class LogRecord:
	def __init__(self, name, level, pathname, lineno, msg, args, exc_info, func=None, sinfo=None):
		#ct = utime.time()
		#self.created = ct
		ct=machine.RTC().datetime()
		self.created = machine.RTC().datetime()
		#self.msecs = (ct - int(ct)) * 1000
		self.msecs= ct[7]
		self.name = name
		self.levelno = level
		self.levelname = _level_dict.get(level, None)
		self.pathname = pathname
		self.lineno = lineno
		self.msg = msg
		self.args = args
		self.exc_info = exc_info
		self.func = func
		self.sinfo = sinfo
