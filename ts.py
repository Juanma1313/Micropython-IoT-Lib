##########################################
## Python module for timestamps         ##
##                                      ##
## Written by Juanma					##
##########################################
import Logging as logging
logger = logging.getLogger(__name__) 
logger.log(logging.DEBUG,"Module [{}] loading",__name__)
import sys, network, machine, time, ntptime

class timestamp:
	# This attributes are global to the class
	main_instance=None
	synced = False
	lastsync = None     # Timestamp of lst sinchronization, secconds is enough resolution
	max_sync_interval=None
	ntp_server=None
	deltatime=0
	
	def __init__(self, ntp_server = None, max_sync_interval = 3600, deltatime = time.mktime((2020, 1, 1, 0, 0, 0, 0, 0)), time_offset=0):
		if self.main_instance == None:
			self.main_instance=self	# maintain a instance to itselve so it does not terminate if not referenced
			logger.log(logging.DEBUG,__class__.__name__+".__init__({}): New instance", ntp_server)
			self.max_sync_interval=max_sync_interval
			self.deltatime = deltatime + time_offset	# All float dates are starting from this date. to increase resolution because we only have 32 bits and it encodes up to microsecconds
														# do not forget to add this value to get correct gmt date
			self.ntp_sync(ntp_server )
		
	def ntp_sync(self, ntp_server = None ):
		if ntp_server != self.ntp_server:
			self.ntp_server =ntp_server
			
		if not self.ntp_server:
			self.ntp_server = ntptime.host
			logger.log(logging.WARNING,__class__.__name__+".ntp_sync(): NTP server not define, using default:[{}] ", ntp_server)
		
		if self.synced and self.ntp_server==ntptime.host:	return True

		logger.log(logging.DEBUG,__class__.__name__+".ntp_sync({}): Sync request", ntp_server)
		
		try:
			ntptime.host=self.ntp_server
			ntptime.settime()
		except Exception as e:
			sys.print_exception(e)
			logger.log(logging.ERROR,__class__.__name__+".ntp_sync({}): Sync error: {}", self.ntp_server, e)
			return False
		self.synced = True    
		self.lastsync = time.time()     # Timestamp of lst sinchronization, secconds is enough resolution
		return True

	def ntp_synced(self):
		if not self.synced or time.time() - self.lastsync > self.max_sync_interval:     # We have exceded the time interval between synchronizations
			self.synced = False
			return self.ntp_sync()
		else:
			return self.synced
		
	def timestamp(self):
		return time.time() 

	def timestamp_float_str(self):
		return "{}.{}".format(self.timestamp(), machine.RTC().datetime()[7])
		
	def timestamp_tuple(self):      #  returns following tumplet (year, month, day, weekday, hours, minutes, seconds, microseconds 10^-6 seconds)
		#realtime = self.timestamp_float()
		#return time.gmtime(int(realtime)) + (int((realtime-int(realtime))*10000),) # returns 8 value tuple equivalent to gmtime + miliseconds 
		return machine.RTC().datetime()
		
	
	def timestamp_str(self, format="{0:04}-{1:02}-{2:02}T{4:02}:{5:02}:{6:02}.{7:06}"):
		#realtime = self.timestamp_float()
		
		return format.format(*machine.RTC().datetime())

	def validtime(self, timestamp, timetolive):
		return (self.timestamp_float()-timestamp) <= timetolive

# time.Localtime to RTC.datetime format 
def lt2dt(lt):
	''' time.localtime()/ time.maktime() format
	year includes the century (for example 2014).
	month is 1-12
	mday is 1-31
	hour is 0-23
	minute is 0-59
	second is 0-59
	weekday is 0-6 for Mon-Sun
	yearday is 1-366
	'''
	if not lt: lt=(0,0,0,0,0,0,0,0)	
	return (lt[0],lt[1],lt[2],lt[6],lt[3],lt[4],lt[5],0)  # convert from time.localtime() fromat to machine.RTC().datetime() fromat

# RTC.datetime format  to time.Localtime 
def dt2lt(dt):
	''' machine.RTC.datetime() format
	This format is needed to obtain the subsecond portion for logging, debugging, etc.
	year includes the century (for example 2014).
	month is 1-12
	mday is 1-31
	weekday is 1-7 for Mon-Sun
	hour is 0-23
	minute is 0-59
	second is 0-59
	subseconds
	'''
	if not dt: dt=(0,0,0,0,0,0,0,0)
	return (dt[0],dt[1],dt[2],dt[4],dt[5],dt[6],dt[3],0)  # convert from time.localtime() fromat to machine.RTC().datetime() fromat (yearday is not calculated)

def difftime( t1, t2):
	'''Calculates the time diference between t1 and t2 assuming t1 is older than t2
		t1 and t2 use machine.RTC.datetime() format.
		it uses a non subsecond operations so it can perform in 32 bit floating point
		'''
	# Calculate seconds for both times ignore subsecond
	s1=time.mktime(dt2lt(t1))   # converts to seconds t1
	s2=time.mktime(dt2lt(t2))   # converts to seconds t2
	diff_secs=s2-s1
	diff_subs=t2[7]-t1[7]
	diff_secs+=diff_subs/1000000
	return diff_secs
	
logger.log(logging.DEBUG,"Module [{}] loaded",__name__)
		
