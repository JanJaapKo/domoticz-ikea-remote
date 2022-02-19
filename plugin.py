# plugin to add some behavior to the IKEA STYRBAR remote
#
# Author: Jan-Jaap Kostelijk
"""
<plugin key="IKEA-remote" name="IKEA remote control" author="Jan-Jaap Kostelijk" version="0.1.1" externallink="https://github.com/JanJaapKo/domoticz-ikea-remote">
    <description>
	<br/><h2>IKEA remote control</h2><br/>
    <p>This plugin will let you do the following with the STYRBAR remote control:</p>
    <ul>
        <li>left arrow: previous Zigbee group</li>
        <li>right arrow: next Zigbee group</li>
        <li>brightness up: increase brightness of selected group</li>
        <li>brightness down: decrease brightness of selected group</li>
    </ul>
</description>
    <params>
        <param field="Address" label="MQTT Server address" width="300px" required="true" default="127.0.0.1"/>
        <param field="Port" label="Port" width="300px" required="true" default="1883"/>
        <param field="Mode2" label="Remote control device name" width="300px" required="true" default=""/>
        <param field="Mode3" label="(group) names of zigbee devices, separate by ;" width="300px" required="true"/>
        <param field="Mode4" label="timeout to reset device index to all">
            <options>
                <option label="1 minute" value="6"/>
                <option label="5 minutes" value="30" default="true"/>
                <option label="10 minute" value="60"/>
                <option label="NEVER" value="0"/>
            </options>
        </param>
        <param field="Mode5" label="Type of MQTT topic to listen" required="true">
            <description>Allows selection to listen directly on Z2M topics or using Domoticz out topic.<br/>Z2M leads to crashes now, write is always to Z2M.</description>
            <options>
                <option label="domoticz" value="domoticz" default="true"/>
                <option label="zigbee2mqtt" value="zigbee2mqtt"/>
            </options>
        </param>
        <param field="Mode1" label="Zigbee2Mqtt Topic" width="300px" required="false" default="zigbee2mqtt">
            <description><br/>Only fill when you configured Zigbee2MQTT to use a non-default topic name.<br/>Needed for writing to the lights.</description>
        </param>
        <param field="Mode6" label="Debug" width="75px">
            <options>
                <option label="Verbose" value="Verbose"/>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal" default="true" />
            </options>
        </param>
    </params>
</plugin>
"""

import Domoticz
import json
from mqtt import MqttClient

class IkeaRemotePlugin:
    mqttClient = None
    action_list = ["on", "off", "brightness_move_up", "brightness_move_down", "brightness_stop", "arrow_left_click", "arrow_right_click", "arrow_left_hold", "arrow_right_hold", "arrow_left_release", "arrow_right_release"]
    level_names = {}

    def onStart(self):
        self.debugging = Parameters["Mode6"]
        
        if self.debugging == "Verbose":
            Domoticz.Debugging(2+4+8+16+64)
        if self.debugging == "Debug":
            Domoticz.Debugging(2)
            DumpConfigToLog()

        Domoticz.Debug("Starting plugin")
        self.topic_type = Parameters["Mode5"].strip()
        if self.topic_type == "zigbee2mqtt":
            if len(Parameters["Mode1"].strip()) > 0:
                self.base_topic = Parameters["Mode1"].strip()
            else:
                self.base_topic = "zigbee2mqtt"
        else:
            self.base_topic = "domoticz"
        #self.topic_type = "zigbee2mqtt"
        mqtt_server_address = Parameters["Address"].strip()
        mqtt_server_port = Parameters["Port"].strip()
        mqtt_client_id = ""
        self.mqttClient = MqttClient(mqtt_server_address, mqtt_server_port, mqtt_client_id, self.onMQTTConnected, self.onMQTTDisconnected, self.onMQTTPublish, self.onMQTTSubscribed)

        self.devicelist = Parameters["Mode3"].split(";")
        self.devicelist.insert(0, "all")
        Domoticz.Log("Starting to control the following devices:")
        for device in self.devicelist:
            Domoticz.Log(" - " + device)
        self.device_index = 0
        self.remote = Parameters["Mode2"].strip()

        self.resetTime = int(Parameters["Mode4"])
        if self.resetTime == 0:
            self.reset = False
        else:
            self.reset = True
        self.pollcount = 3

    def onStop(self):
        Domoticz.Debug("onStop called")
        self.mqttClient.close()

    def onHeartbeat(self):
        self.pollcount = self.pollcount - 1
        if self.pollcount <= 0:
            self.mqttClient.onHeartbeat()
            self.pollcount = 3
        if self.reset:
            self.resetTime = self.resetTime - 1
            if self.resetTime <= 0:
                Domoticz.Debug("onHeartbeat called, reset selected device.")
                self.device_index = 0
                self.resetTime = int(Parameters["Mode4"])
                Domoticz.Log("Selected device: '"+str(self.device_index)+"': '"+self.devicelist[self.device_index]+"'")
            else:
                Domoticz.Debug("Selected device: '"+str(self.device_index)+"': '"+self.devicelist[self.device_index]+"'")

    def onConnect(self, Connection, Status, Description):
        Domoticz.Debug("onConnect called")
        self.mqttClient.onConnect(Connection, Status, Description)

    def onDisconnect(self, Connection):
        Domoticz.Debug("onDisonnect called")
        self.mqttClient.onDisconnect(Connection)

    def onMessage(self, Connection, Data):
        self.mqttClient.onMessage(Connection, Data)

    def onMQTTConnected(self):
        Domoticz.Debug('Connected to MQTT server')
        #subscribe to the topic of the remote to listen to incoming events
        if self.topic_type == "zigbee2mqtt":
            self.mqttClient.subscribe([self.base_topic + '/' + self.remote])
        elif self.topic_type == "domoticz":
            self.mqttClient.subscribe([self.base_topic + '/out/' + self.remote])

    def onMQTTDisconnected(self):
        Domoticz.Debug('Disconnected from MQTT server')

    def onMQTTSubscribed(self):
        Domoticz.Debug('Subscribed to "' + self.base_topic + '/'+self.remote+'" topic')

    def onMQTTPublish(self, topic, message):
        if message is not None:
            Domoticz.Debug("MQTT mssage received: " + topic + " message: " + str(message))
        else:    
            Domoticz.Debug("MQTT mssage received: " + topic + " message: is None")
        action = "" 
        if self.topic_type == "zigbee2mqtt":
            if "action" in message:
                #when reading from zigbee2mqtt
                action = message["action"]
                if action not in self.action_list:
                    Domoticz.Debug("Action '" +action+"' not in action list")
                    return
        if self.topic_type == "domoticz":
            #when reading from domoticz/out
            if len(self.level_names)==0:
                #make transation dictionary from levels numeric to string
                levels = message["LevelNames"].split("|")
                for i in range(len(levels)):
                    self.level_names[i*10] = levels[i]
                    Domoticz.Debug("adding level number "+str(i)+": "+levels[i])
            Domoticz.Debug("received key: svalue: "+str(message["svalue1"])+" which is action: "+self.level_names[int(message["svalue1"])])
            action = self.level_names[int(message["svalue1"])]
        #on arrow click, select next/prev device in list (0 = all)
        #blink the selected light to confirm
        if action in ("arrow_left_click","arrow_right_click"):
            if action == "arrow_left_click":
                self.device_index -=1
                if self.device_index < 0:
                    self.device_index = len(self.devicelist) - 1
            elif action == "arrow_right_click":
                self.device_index +=1
                if (len(self.devicelist) - 1) < self.device_index:
                    self.device_index = 0
            #have the selected light blink to confirm selection
            if self.device_index > 0:
                command = {"effect":"blink"}
                self.send_command(command,self.devicelist[self.device_index])
            return
        if action in ("on", "off"):
            command = {"state":action}
            self.send_command(command, self.devicelist[self.device_index])
        else:
            Domoticz.Debug("Action '"+action+"' not implemented")
        if action in ("brightness_move_up", "brightness_move_down", "brightness_stop"):
            move_speed = 0
            if action == "brightness_move_up":
                move_speed = 25
            elif action == "brightness_move_down":
                move_speed = -25
            elif action == "brightness_stop":
                move_speed = 0
            command = {"brightness_move" : move_speed}
            self.send_command(command, self.devicelist[self.device_index])
        Domoticz.Debug("Selected device: '"+str(self.device_index)+"': '"+self.devicelist[self.device_index]+"'")
            
    def send_command(self, action, device):
        topic = ""
        payload = json.dumps(action)
        if device == "all":
            for device in self.devicelist:
                topic = self.base_topic + '/' + str(device) + '/set'
                self.mqttClient.publish(topic, payload)
        else:
            topic = self.base_topic + '/' + str(device) + '/set'
            self.mqttClient.publish(topic, payload)

global _plugin
_plugin = IkeaRemotePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug("'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
    return


def DumpHTTPResponseToLog(httpDict):
    if isinstance(httpDict, dict):
        Domoticz.Debug("HTTP Details (" + str(len(httpDict)) + "):")
        for x in httpDict:
            if isinstance(httpDict[x], dict):
                Domoticz.Debug("--->'" + x + " (" + str(len(httpDict[x])) + "):")
                for y in httpDict[x]:
                    Domoticz.Debug("------->'" + y + "':'" + str(httpDict[x][y]) + "'")
            else:
                Domoticz.Debug("--->'" + x + "':'" + str(httpDict[x]) + "'")
