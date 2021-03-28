##########################################
## Python module for IoT                ##
##                                      ##
## Written by Juanma					##
##########################################
import Logging as logging
logger = logging.getLogger(__name__)   # Gets the logger that should be stablished in setup or main, but if not, it creates  new one in DEBUG mode
logger.level=logging.DEBUG
logger.log(logging.DEBUG,"Module [{}] loading",__name__)

import ts, msgs
from MQTT_slim import MQTTClient     

import io,json, time, network, machine, binascii, os, sys

NETWORK_STATE={
    network.STAT_IDLE: "STAT_IDLE",
    network.STAT_CONNECTING: "STAT_CONNECTING",
    network.STAT_GOT_IP: "STAT_GOT_IP",
    network.STAT_NO_AP_FOUND: "STAT_NO_AP_FOUND",
    network.STAT_WRONG_PASSWORD: "STAT_WRONG_PASSWORD",
    network.STAT_BEACON_TIMEOUT: "STAT_BEACON_TIMEOUT",
    network.STAT_ASSOC_FAIL: "STAT_ASSOC_FAIL",
    network.STAT_HANDSHAKE_TIMEOUT: "STAT_HANDSHAKE_TIMEOUT",
    }

SENSOR_DATA_IDLE	=const(0)
SENSOR_DATA_PULL	=const(1)
SENSOR_DATA_PUSH	=const(2)
SENSOR_CONTROL 		=const(4)

#IoT Events reported by callback
EVT_MQTT_Unknown	=const(0)
EVT_MQTT_rcv_msg	=const(1)
EVT_Sensor_Push_data=const(2)

__version__ = "0.1.1"
__author__ = "Juan Manuel de las Heras"
__license__ = "Apache-2.0"

#Special Dictionary Tree search functions formats
IOT_MODE=const(0)	# for path input or output 	Example: "sensors/buttons/values"
DIC_MODE=const(1)	# for path output ready for eval() function. Example: "['sensors']['buttons']['values']"

def find_key(dic, key, mode=IOT_MODE, level=0,  ):
    level+=1
    for k in dic.keys():
        #print("level({}), check({})".format(level, k))
        if k == key:
            #print("level({}), found({})".format(level, k))
            if mode is IOT_MODE:
                return key
            elif mode is DIC_MODE:
                return "['{}']".format(key)
            #return key
        else:
            if type(dic[k]) is dict:
                #return "{}/{}".format(k, find_key(dic[k], key, level))
                result=find_key(dic[k], key, mode, level)
                if result:
                    if mode is IOT_MODE:
                        return "{}/{}".format(k, result )
                    elif mode is DIC_MODE:
                        return "['{}']{}".format(k,result )
    return ""

def find_val(dic, val, mode=IOT_MODE):
    for k, v in dic.items():
        #print("check({})".format((k, v)))
        if v is val:
            #print("Found k({}) v({})".format(k, v))
            if mode is IOT_MODE:
                return k
            elif mode is DIC_MODE:
                return "['{}']".format(k)
        else:
            if type(v) is dict:
                result=find_val(v, val, mode)
                if result:
                    if mode is IOT_MODE:
                        return "{}/{}".format(k, result )
                    elif mode is DIC_MODE:
                        return "['{}']{}".format(k,result )
    return ""

def find_path(dic, path, mode=IOT_MODE):
    retval=[]
    org = dic
    def list_paths(dic):
        nonlocal retval, org, path, mode
        #if not org: org=dic
        for k, v in dic.items():
            p=find_val(org, v)
            #print("key({}) path({}){}".format( k, p, "<< FOUND" if p.endswith(path) else "" ))
            if p.endswith(path):
                if mode is IOT_MODE:
                    retval.append(p)
                elif mode is DIC_MODE:
                    retval.append("['{}']".format(p.replace("/","']['")))
            if type(dic[k]) is dict:
                list_paths(dic[k])
        return retval
    return list_paths(dic)

class Config:
    version=__version__
    def __init__(self, config=None): # receive all the attributes as a dictionary
        if type(config)==dict:
            for k,v in config.items():
                if type(v) is str and v.startswith("bytearray("):		
                    v=eval(v)	# converts back str to bytearray
                setattr(self, k, v)
    def load(self,file_name):
        try:
            f=io.open(file_name, mode='r')
            self.__init__(json.load(f))
            f.close()
        except Exception as e:
            logger.log(logging.WARNING,"Config.load({}) error:Exception:{}",file_name, e)
            return False
        return True	# Config was loaded correctly
    def save(self,file_name):
        try:
            d=self.__dict__
            for k,v in d.items():
                if type(v) is bytearray:
                    d[k]="bytearray({})".format(bytes(v))	# converts  bytearray to str
            f=io.open(file_name, mode='w')
            json.dump(d, f)
            f.close()
        except Exception as e:
            sys.print_exception(e)
            logger.log(logging.WARNING,"Config.save({}) error:Exception:{}",file_name, e)
            return False
        return True	# Config was loaded correctly

class Device:
    _config_file=b"Config.cfg"
    _config=None
    _timestamp=None
    _mqtt=None
    def __init__(self, name, config=None):
        if type(config) is Config:	
            self._config=config	
        else:						# config is not an iot.Config object
            self._config=Config()	# Creates new config object
            if type(config) is str:		# config is a filename
                self._config_file=config	# Stores file_name for future use
            if not self.load_config():	#cannot load the config from the file
                self._def_config()		# create a default config
        logger.log(logging.DEBUG,__class__.__name__+".__init__ name={}", name)
        if type(name) == str: name = name.encode(b"UTF8")
        self.name=name
        self._callback=None			# Callback for IoT events
        self._device_tree_init()	# creates the device tree
        
        
    def _def_config(self):
        logger.log(logging.DEBUG,__class__.__name__+"._def_config()")
        c=self._config
        c.version=__version__
        c.netw_name=bytearray(os.uname().nodename)	# Set in os.uname
        c.netw_type=network.AP_IF      	# set in network.WLAN(netw_type)  //  network.STA_IF=Station, network.AP_IF=AccessPoint
        c.netw_mac="{:02x}:{:02x}:{:02x}:{:02x}:{:02x}:{:02x}".format(*list(network.WLAN(network.AP_IF).config("mac")))	## READ ONLY
        c.netw_channel=0      			# set in network.WLAN(AccessPoint).config("channel") ## ONLY FOR netw_type=1=(AccessPoint)
        c.netw_hidden=False            	# set in network.WLAN(AccessPoint).config("channel") ## READ ONLY // ONLY FOR netw_type=1=(AccessPoint)
        c.netw_authmode=0              	# set in network.WLAN(AccessPoint).config("authmode") ## ONLY FOR netw_type=1=(AccessPoint) // 0=open, 1=WEP, 2=WPA-PSK, 3=WPA2-PSK, 4=WPA/WPA2-PSK
        c.netw_essid=c.netw_name         # set in network.WLAN(netw_type).connect(netw_ssid, pass), or network.WLAN(netw_type).config("essid")
        c.netw_password=""
        c.netw_ip			=b"192.168.13.1"     	# set in network.WLAN(netw_type).ifconfig()[0]
        c.netw_subnet		=b"255.255.255.0"   	# set in network.WLAN(netw_type).ifconfig()[1]
        c.netw_gateway		=b"192.168.13.1"       	# set in network.WLAN(netw_type).ifconfig()[2]
        c.netw_dns			=b"192.168.13.1"      	# set in network.WLAN(netw_type).ifconfig()[3]
        c.ntp_svr			=b"192.168.1.1"     	# set in ntptime.host=ntp_svr; ntptime.settime()
        c.ntp_offset=0                 	# set in ntptime.NTP_DELTA+=ntp_offset ; ntptime.settime() (in seconds)
        c.dhcp=None						#set in network.WLAN(netw_type).config("dhcp_hostname") ## READ ONLY 
        c.mqtt_broker		=b"192.168.1.1"
        c.mqtt_port=1883
        c.mqtt_username=None
        c.mqtt_password=None
        c.mqtt_path="IoT/devices"
        c.ftp_enabled=True				# Enables FTP for config
        c.iot_enabled=False				# do not enable IoT, we need first to configure
        c.iot_name=c.netw_name
        c.iot_type=bytearray(b'device')
        c.iot_id=bytearray(binascii.hexlify(machine.unique_id())) # usually this coincide with MAC address network.WLAN(netw_type).config("mac")
    @property
    def name(self):
        return self._config.iot_name
    @name.setter
    def name(self, newname):
        c=self._config
        logger.log(logging.WARNING,__class__.__name__+".name=({},{}) netw_name: prev=({},{})", type(newname), newname,  type(c.netw_name), c.netw_name )
        c.netw_name[:]=newname
        c.iot_name[:]=newname
    @property
    def type(self):
        return self._config.iot_type
    @property
    def id(self):
        return self._config.iot_id
        return c
    def save_config(self, file_name=None):
        self._config.version=__version__	#Update version to configuration
        if file_name:
            if self._config.save(file_name):	# if succescuffy saved on new filename
                self._config_file=file_name
                retval=True
        else:
            retval=self._config.save(self._config_file)
        return retval
    def load_config(self, file_name=None):
        retval=False
        if not file_name:	# Filename specified
            file_name=self._config_file
        if self._config.load(file_name):	# if succescuffy loaded from filename
            self._config_file=file_name
            retval=True
            if self._config.version!=__version__:	# Version check and warn if different
                logger.log(logging.WARNING,__class__.__name__+".load_config({}):ver.[{}] differs from Module ver.[{}] ",file_name, self._config.version, __version__)
        return retval
    def _device_tree_init(self):
        logger.log(logging.DEBUG,__class__.__name__+"._device_tree_init")	
        c=self._config
        self._device_tree={
                "name":self.name,
                "registration":{
                    "name":self.name,
                    "id":self.id,
                    "type":self.type,
                    "root_topic":None},
                "sensors":{},
                    }
    def set_callback(self, callback):	# sets a callback function to report all IoT events
        self._callback=callback
    def start_device(self):				# Starts Network, register device, Notify availability
        logger.log(logging.DEBUG,__class__.__name__+".start_device()")	
        self.start_net()
        if not self._config.iot_enabled:	# The device is not enabled, lets run the interactive web prompt
            return False
        time.sleep(1)
        self.start_mqtt()	# Start the connection with the MQTT broker
        time.sleep(1)
        self.register()		# Register de device on the MQTT broker
        time.sleep(1)
        self.available()	# Notify to subscribers that the device is available
        return True
    def start_net(self): # Network startup
        c=self._config
        if c.netw_type==network.AP_IF:
            network.WLAN(c.netw_type).active(True)
            network.WLAN(c.netw_type).config(essid=c.netw_essid.decode())
            network.WLAN(c.netw_type).config(channel=c.netw_channel)
            network.WLAN(c.netw_type).config(authmode=c.netw_authmode, password=c.netw_password)
            network.WLAN(c.netw_type).config(hidden=c.netw_hidden)
            network.WLAN(c.netw_type).ifconfig((c.netw_ip, c.netw_subnet, c.netw_gateway, c.netw_dns))
        else:
            network.WLAN(c.netw_type).active(True)
            network.WLAN(c.netw_type).ifconfig((c.netw_ip, c.netw_subnet, c.netw_gateway, c.netw_dns))
            network.WLAN(c.netw_type).connect(c.netw_essid, c.netw_password)
            s=network.STAT_CONNECTING
            while s==network.STAT_CONNECTING:
                logger.log(logging.DEBUG,__class__.__name__+".start_net('{}'): {}",c.ntp_svr, NETWORK_STATE[s])
                time.sleep(1)
                s=network.WLAN(c.netw_type).status()
            if s in NETWORK_STATE:
                logger.log(logging.DEBUG,__class__.__name__+".start_net('{}'): {}",c.ntp_svr, NETWORK_STATE[s])
            else:
                logger.log(logging.ERROR,__class__.__name__+".start_net('{}'): Network status [{}] unknown.",c.ntp_svr, s)
                
            if not self.start_ntp():
                logger.log(logging.DEBUG,__class__.__name__+".start_net('{}'):NTP Not synced",c.ntp_svr)
            else:
                logger.log(logging.DEBUG,__class__.__name__+".start_net('{}'):NTP synced",c.ntp_svr)	
        logger.log(logging.DEBUG,__class__.__name__+".start_net():Network config:{}", network.WLAN(c.netw_type).ifconfig())
    def start_ntp(self): # NTP startup   
        c=self._config
        self._timestamp = ts.timestamp( ntp_server=c.ntp_svr )
        logger.log(logging.DEBUG,__class__.__name__+".start_ntp('{}'):Syncing",c.ntp_svr)
        tmo = 10
        while not self._timestamp.ntp_synced():
            self._timestamp.ntp_sync(ntp_server=c.ntp_svr )
            time.sleep_ms(1000)
            tmo -= 1
            if tmo == 0:
                break
        return self._timestamp.ntp_synced()

    def _mqtt_callback(self, topic, msg):
        logger.log(logging.DEBUG,__class__.__name__+"._mqtt_callback(topic={}, msg={})",topic, msg)
        if self._callback:
            try:
                data=json.loads(msg)
                #TODO: Process "tst", "ttl" and avoid expired data  
                #logger.log(logging.DEBUG,__class__.__name__+"._mqtt_callback(data={})",data)
                for item,value in data.items():
                    if item=="pld":  # data is valid payload
                        if type(topic)==bytes:  
                            topic=topic.decode()
                        self._callback(event=EVT_MQTT_rcv_msg, args=(topic, value) )
            except Exception as e:
                #sys.print_exception(e)
                logger.log(logging.DEBUG,__class__.__name__+".start_mqtt(client_id={}, broker={}, port={}, user={}):MQTT Connecting, Exception:[{}]", client_id, c.mqtt_broker, c.mqtt_port, user, e)
                

    def start_mqtt(self):
        c=self._config
        client_id=self.id.decode("UTF-8") if self.id else None
        user=c.mqtt_username.decode("UTF-8") if c.mqtt_username else None
        password=c.mqtt_password.decode("UTF-8") if c.mqtt_password else None
        logger.log(logging.DEBUG,__class__.__name__+".start_mqtt(client_id={}, broker={}, port={}, user={}):MQTT Connecting", client_id, c.mqtt_broker, c.mqtt_port, user)
        self._mqtt = MQTTClient(client_id = client_id, 
                            server = c.mqtt_broker, 
                            port=c.mqtt_port, 
                            user = user, 
                            password=password)
        self._mqtt.set_callback(self._mqtt_callback)
        try:
            self._mqtt.connect()
        except Exception as e:
            sys.print_exception(e)
            logger.log(logging.DEBUG,__class__.__name__+".start_mqtt(client_id={}, broker={}, port={}, user={}):MQTT Connecting, Exception:[{}]", client_id, c.mqtt_broker, c.mqtt_port, user, e)
            return
        try:
            topic=None
            self._device_tree["registration"]["root_topic"]="/".join((self._config.mqtt_path,self.name.decode(b'UTF-8')))
            topic="/".join((self._device_tree["registration"]["root_topic"],"#"))
            logger.log(logging.DEBUG,__class__.__name__+".start_mqtt():MQTT Subscribing, Topic:[{}]", topic)
            self._mqtt.subscribe(topic)
        except Exception as e:
            sys.print_exception(e)
            logger.log(logging.DEBUG,__class__.__name__+".start_mqtt():MQTT Subscribing, Topic:[{}], exception [{}]",topic, e)
        logger.log(logging.DEBUG,__class__.__name__+".start_mqtt():MQTT Subscribed, Topic:[{}]", topic)
    def register(self):		# Register the device on the designated MQTT broker, opens  defined publications and subscriptions
        try:
            topic = "/".join((self._config.mqtt_path,"registration")) 
            msg=msgs.message(timestamp=self._timestamp.timestamp_str(), timetolive=0, payload=self._device_tree["registration"])
            logger.log(logging.DEBUG,__class__.__name__+".register(): topic={}, msg={}",topic, msg)
            self._mqtt.publish(topic, msg, retain=True, qos=0) # make a retain publication pf registration information
        except Exception as e:
            sys.print_exception(e)
            logger.log(logging.DEBUG,__class__.__name__+".register():MQTT publishing registration , Exception:[{}]", e)
    def available(self):	# Notifies to subscribers device availability
        logger.log(logging.DEBUG,__class__.__name__+".available()")
        try:
            topic = "/".join((self._config.mqtt_path,"device")) 
            msg=msgs.message(timestamp=self._timestamp.timestamp_str(), timetolive=0, payload=self._device_tree["registration"])
            logger.log(logging.DEBUG,__class__.__name__+".available(): topic={}, msg={}",topic, msg)
            self._mqtt.publish(topic, msg, retain=False, qos=0) # make a retain publication pf registration information
        except Exception as e:
            sys.print_exception(e)
            logger.log(logging.DEBUG,__class__.__name__+".available():MQTT publishing registration , Exception:[{}]", e)
    def del_sensor(self, sensor):
        pass # TODO:
    def addsensor(self, path, name, sensor, callback=None):	# name is just a label, [sensor] must be the sensor object, [data] must be a sensorfunction dictionary with values.
        #tree_str=find_path(self._device_tree, path, DIC_MODE )		# in micropython we can't use  eval() function because it only works with global variables
        tree=self._device_tree["sensors"]
        tree[name]={
                "name":name,
                "object":sensor,
                }	
        if not callback: callback=self._sensor_callback
        sensor.set_callback(callback)
    #def add_sensor_data(self, sensor, name, data, type=SENSOR_DATA_PULL, pull_freq=60):	# name is just a label, [sensor] must be the sensor object, [data] must be a sensorfunction dictionary with values.
    #	#TODO: ONGOING
    #	sensor_tree=find_val(self._device_tree, sensor, DIC_MODE )
    #	if sensor_tree:
    #		tree["data"][name]={
    #				"name": name,
    #				"data":data,
    #				"type":type,
    #				"freq":pull_freq,
    #				}	
    def _sensor_callback(self, sensor:Sensor, data:Value )->None:		# callback used by sensors to push data to clients. data should be a dictionary registered in device._device_tree.
        # search for previously registered sensor, pull data and publish it into MQTT Broker
        #logger.log(logging.DEBUG,__class__.__name__+"._sensor_callback(sensor=[{}], data=[{}])",sensor, data)
        # Report event to application
        if self._callback:
            self._callback(event=EVT_Sensor_Push_data, args=(sensor, data) )
        # Publicate event
        path=find_val(self._device_tree, sensor, IOT_MODE )
        if path:
            
            topic = "/".join((self._device_tree["registration"]["root_topic"],path)) 
            msg= data.read()	# read the data from sensor 
            #for i  in range(len(msg)):
            #	if type(msg[i]) is bytearray: msg[i]=msg[i].decode()	# converts bytearray to str
            msg=json.dumps({"tst": self._timestamp.timestamp_str(), "pld": msg})
            logger.log(logging.DEBUG,__class__.__name__+"._sensor_callback(): topic={}, msg={}",topic, msg)
            self._mqtt.publish(topic, msg, retain=True, qos=0) # make a retain publication pf registration information
    def process(self)-> int:
        self._mqtt.check_msg() # process MQTT message queues
        #tree_str=find_path(self._device_tree, "sensors", DIC_MODE ) # in micropython we can't use  eval() function because it only works with global variables
        tree=self._device_tree["sensors"]
        i=0	# counts the number of sensors process called
        timestamp=self._timestamp.timestamp_tuple()
        for name, sensor in  tree.items():
            i+=sensor["object"].process(timestamp)		# count  processed values
        return i

class Sensor:
    def __init__(self, callback:Callable[[Value], None]=None):
        self._values=[]	# initializes the values list
        self._callback=callback
    def addvalue(self, name, get, freq_max=None, freq_min=None, type=None, read=None) -> None:
        self._values.append(Value(name=name, get=get, freq_max=freq_max, freq_min=freq_min, type=type, read=read , callback=self.values_callback))
    def values_callback(self, value: Value) -> None:
        #logger.log(logging.DEBUG,__class__.__name__+".values_callback: msg={}",value)
        self._callback(self, value)
    def set_callback(self, callback:Callable[[Value], None]):	# sets the function to call when data is ready to be transmited to Device
        self._callback=callback
    def process(self, timestamp)->int:	# Called by Device.process() every cicle
        self._process(timestamp)	# Calls the sensor driver process method
        #TODO: recovers sensor, produces data, checks push, returns pulls
        i=0
        for value in self._values:
            i+= value.process(timestamp)	# count  processed values
        return i
# this clash define the value or group of values that share frequency and pull/push characteristics 
# Note, usually get() and read() should return the same values but only get() actually reads from the sensor.
class Value:
    def __init__(self, name, get, freq_max=None, freq_min=None, type=None, read=None , callback:Callable[[Value], None]=None):
        self._name=name			# just a label for the value 
        self._type = type	
        self._read = read		# function to read the allready processed sensor value that should return single value or  a dictionary {"name1":Value1,"name2":value2,..} of values
        self._get = get			# function to get the value from the sensor
        self._freq_max=freq_max	# max number of gets/callbacks per second allowed
        self._freq_min=freq_min	# minimum number of gets/callbacks per second (in case the sensor could undergo buffer overflow)
        self._callback=callback	# callback funtion for push data
        self._last_get=(0,0,0,0,0,0,0,0)
        self._flg_read=False
        self._flg_push=False

    def get(self):
        return self._get()
    def read(self):
        return self._read()
    def process(self, timestamp)->int:	# Cheks if it is time for the value to be pulled or pushed
        t = ts.difftime(self._last_get, timestamp)
        if (t and ((1/t)<self._freq_min) or (self._flg_push and (1/t)<self._freq_max)):	# the last value is below the minimum threshold. we must puch a value
            self._flg_read=False
            self._last_get=timestamp
            self.get()
            if self._type & (SENSOR_DATA_PUSH | SENSOR_CONTROL):
                self._callback(self)
            self.read()
            self._flg_push=False	# resets push flag if set
            return 1
        else:
            self._flg_push=False	# resets push flag if set
            return 0

        
        
        

logger.log(logging.DEBUG,"Module [{}] loaded",__name__)
