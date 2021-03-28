##########################################
## Python module for IoT message formats##
##                                      ##
## Written by Juanma					##
##########################################
import Logging as logging
logger = logging.getLogger(__name__)
logger.log(logging.DEBUG,"Module [{}] loading",__name__)
import json

MSG_TimeStamp   = "ts"
MSG_TimeToLive  = "ttl"
MSG_Payload     = "pld"

def message(timestamp, timetolive, payload):
	msg={}
	for k,v in payload.items():
		if type(v) is bytearray: payload[k]=v.decode()	# converts bytearray to str

	msg.update({MSG_TimeStamp: timestamp})
	msg.update({MSG_TimeToLive: timetolive})
	msg.update({MSG_Payload: payload})
	return json.dumps(msg)
	
logger.log(logging.DEBUG,"Module [{}] loaded",__name__)
