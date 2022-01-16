# plugin to add some behavior to the IKEA STYRBAR remote
#
# Author: Jan-Jaap Kostelijk
"""
<plugin key="IKEA-remote" name="IKEA remote control" author="Jan-Jaap Kostelijk" version="0.1.0" externallink="https://github.com/JanJaapKo/domoticz-ikea-remote">
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
        <param field="Mode1" label="Zigbee2Mqtt Topic" width="300px" required="true" default="zigbee2mqtt"/>
        <param field="Mode2" label="Remote control device name" width="300px" required="true" default=""/>
        <param field="Mode3" label="(group) names of zigbee devices, separate by ;" required="true"/>
        <param field="Mode4" label="timeout to reset device index to all">
            <options>
                <option label="10 sec" value="1" default="true"/>
                <option label="30 sec" value="3"/>
                <option label="1 minute" value="6"/>
            </options>
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

    def onStart(self):
        self.debugging = Parameters["Mode6"]
        
        if self.debugging == "Verbose":
            Domoticz.Debugging(2+4+8+16+64)
        if self.debugging == "Debug":
            Domoticz.Debugging(2)

        Domoticz.Debug("Starting plugin")
        self.base_topic = Parameters["Mode1"].strip()
        mqtt_server_address = Parameters["Address"].strip()
        mqtt_server_port = Parameters["Port"].strip()
        mqtt_client_id = ""
        self.mqttClient = MqttClient(mqtt_server_address, mqtt_server_port, mqtt_client_id, self.onMQTTConnected, self.onMQTTDisconnected, self.onMQTTPublish, self.onMQTTSubscribed)

        self.devicelist = Parameters["Mode3"].split(";")
        self.devicelist.insert(0, "all")
        self.device_index = 1
        self.remote = Parameters["Mode2"].strip()

        self.resetTime = int(Parameters["Mode4"])


    def onStop(self):
        Domoticz.Debug("onStop called")

    def onHeartbeat(self):
        self.mqttClient.onHeartbeat()
        self.resetTime = self.resetTime - 1
        if self.resetTime <= 0:
            Domoticz.Debug("onHeartbeat called, reset selected device.")
            self.device_index = 1

            self.resetTime = int(Parameters["Mode4"])
        else:
            Domoticz.Debug("onHeartbeat called, run again in " + str(self.resetTime) + " heartbeats.")

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
        self.mqttClient.subscribe([self.base_topic + '/' + self.remote])

    def onMQTTDisconnected(self):
        Domoticz.Debug('Disconnected from MQTT server')

    def onMQTTSubscribed(self):
        Domoticz.Debug('Subscribed to "' + self.base_topic + '/'+self.remote+'" topic')

    def onMQTTPublish(self, topic, message):
        Domoticz.Debug("MQTT message received: " + topic + " " + str(message))
        


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
