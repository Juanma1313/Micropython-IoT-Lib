IoT library for Micro-python
===========================
THIS LIBRARY IS UNDER CONSTRUCTION

This project attempts to create a small library that allows to easily 
define sensors, controllers and all type of devices to control or be 
controlled trough a network in the IoT fashion.

- This library is based on the following  set of assumptions:
	* MQTT or similar protocol is being used for data transmission
	* TCP-UDP is being used for network transport
	* JSON format is used for data encapsulation.

Files:
------
	* Logging.py 	--> logging execution traces.
		Clases:
			``FileHandler``
			``Formatter``
			``Handler``
			``LogRecord``
			``Logger``
			``StreamHandler``
		Functions:
			``basicConfig``
			``debug``
			``getLogger``
			``info``
		Constants:
			``CRITICAL``
			``ERROR``
			``WARNINIG``
			``INFO``
			``DEBUG``
			``NOTSET``
		Dependences:
			machine
			sys
			io
	* ts.py			--> Network Timestamp calculations and translations.
		Clases:
			``timestamp``
		Functions:
			``lt2dt``
			``dt2lt``
			``difftime``
		Constants: None
		Dependences:
			Logging
			machine
			network
			ntptime
			sys
			time
	* MQTT_slim/__init__		--> MQTT publishing and subscribing.
		Clases:
			``MQTTException``
			``MQTTClient``
		Functions: None
		Constants: None
		Dependences:
			Logging
			socket
			ustruct
			ubinascii.hexlify
			ussl (if available)
	* msgs.py		--> Message creation
		Clases: None
		Functions:
			``message``
		Constants:
			``MSG_TimeStamp``
			``MSG_TimeToLive``
			``MSG_Payload``
		Dependences:
			Logging
	* iot.py		--> Devices and Sensors handling
		Clases:
			``Config``
			``Device``
			``Sensor``
			``Value``
		Functions:
			``find_key``
			``find_val``
			``find_path``
		Constants:
			``NETWORK_STATE`` - (dictionary with network state descriptions)
			``SENSOR_DATA_IDLE``
			``SENSOR_DATA_PULL``
			``SENSOR_DATA_PUSH``
			``SENSOR_CONTROL``
			``EVT_MQTT_Unknown``
			``EVT_MQTT_rcv_msg``
			``EVT_Sensor_Push_data``
			``IOT_MODE``
			``DIC_MODE``
		Dependences:
			Logging
			msgs
			ts
			MQTT_slim.MQTTClient 
			binascii
			io
			json
			machine
			network
			os
			sys
			time

Devices and Sensors handling
============================

Device:
-------
Is the highest hierarchy of all IoT entity.
It is capable to register to a broker and send or receive information
about state or operation of itself or any sensor or controller owned 
by itself.
In this early version is not contemplated to have nested devices, but 
the idea is not discarded for future versions. Devices are stand-alone 
entities each one define its own device_tree.

Sensor and controllers:
----------------------
Is the next level of hierarchy for IoT entities. 
It handles all data from/to a physical or virtual sensor or device.
Commands relayed by brokers will be processed by the corresponding 
device and will be feed to the appropriate controller that will physically
contact with the controlled item.
A device can host several sensors or controllers in a series, but at this
point it cannot host them in a nested fashion.
Sensors can produce data and events sync. or asynchronously, and it
will be feed to the device for processing and possibly relaying it.
Controllers can receive events and data from the device and act upon the
physical unit accordingly.
It is possible to have a unit that because its nature can perform as a 
sensor and as a controller that is why all sensors and controllers share
the same class ``Sensor``

Examples of physical sensors can be buttons, joysticks, temperature 
sensors, humidity sensors, touch sensors, accelerometers, etc.
Examples of physically controlled units can be LEDs, LED strips, screens, 
fans, motors, speakers, buzzers, etc.
Examples of hybrid sensor/controller units can be servos, sonoff switches, 
oximeters, mpg players, modems, house apliances, etc.

Values:
-------
Is the basic unit of information handled from/to a sensor and can be 
feed as an event or synchronously pushed or pulled by the device.

Messages:
---------
All information exchanged between devices and brokers are encapsulated 
in messages as JSON strings. the Message contains timestamp, time to live
and device payload containing commands or values from/to the device or
its sensors.

Device tree
------------
This is an internal construction of the ``Device`` class in the form of 
a tree of dictionaries where all the sensors and its values are organized
the application can directly pull or push any Device/sensor value using 
this tree and the device/sensor will act accordingly.

Device tree functions:
----------------------
* ``find_key(dic:dict, key:str, mode:const =IOT_MODE, level:int=0,  ) -> str `` 
	Returns the key path to the first ``key`` that matches in a given 
	dictionary tree. If the key is used more than once in the dictionary
	tree, only the first match will be reported
* ``find_val(dic:dict, val:any, mode:const=IOT_MODE) -> str `` 
	Returns the key path to the first value ``val`` match found in the 
	dictionary tree. If the value is references more than once in the 
	dictionary tree, only the first match will be reported

* ``find_path(dic:dict, path:str, mode:const=IOT_MODE) -> str `` 
	returns a list of all key paths found in the dic tree dictionary, 
	that leads to the given ``path``. 
	``path`` is only supported in ``IOT_MODE``, but output is supported 
	in both ``IOT_MODE`` and ``DIC_MODE`` modes.


*Device_tree descriptor dictionary structure example:
		class Device():
			pass
		class Sensor():
			pass
		class Device_eye(Device):
			pass
		class Device_oxi(Device):
			pass
		class Sensor_butt(Sensor): # button sensor
			def Sleep(self):
				pass
			def Send(self):
				pass
		class Sensor_Joy(Sensor):# joystick sensor
			pass
		class Sensor_max(Sensor): # oximeter sensor
			def Heartrate(self):
				pass
			def spo2(self):
				pass
			def temperature(self):
				pass
		class Sensor_led(Sensor): # rgb led sensor
			def led1(self):
				pass
			def led2(self):
				pass

		device_tree={
				"Name":"oximeter_01",
				"registration":{
					name=self.name,
					id=self.id,
					type=self.type
					root_topic=self._device_subscription
					},
				"Object":Device_oxi(),
				"sensors":{
					"oximeter":{
						"Name":"oximeter",
						"object":Sensor_max(),
						"Values":{
							"rate":Sensor_max().Heartrate,
							"spo2":Sensor_max().spo2,
							"temp":Sensor_max().temperature,
							}
						},
					"buttons":{
						"Name":"buttons",
						"object":Sensor_butt(),
						"Values":{
							"Sleep":Sensor_butt().Sleep,
							"Send":Sensor_butt().Send
							}
						},
					"leds":{
						"Name":"LEDS",
						"object":Sensor_led(),
						"Values":{
							"led1":Sensor_led().led1,
							"led2":Sensor_led().led1
							}
						}
					}
				}

``find_path()`` use example:
----------------------------
	paths=find_path(device_tree, "values", DIC_MODE)
	for s in paths:
		print("{}=".format(s), end="")
		print("{}".format(eval("device_tree"+s)))

* Output:
	['sensors']['buttons']['values']={'sleep': False, 'send': False}
	['sensors']['leds']['values']={'led2': (255, 0, 0), 'led1': (255, 0, 0)}
	['sensors']['oximeter']['values']={'temp': 36.6, 'rate': 59, 'spo2': 99.99}

