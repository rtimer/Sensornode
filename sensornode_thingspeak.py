# sensornode_thingspeak.py
#
# MQTT client for ESP8266 w/ MicroPython & deepsleep mode
# send data locally and to ThingSpeak.
#
# 02/18 HSN

import machine, time
from umqtt import MQTTClient

# set to True for skipping deepsleep
debug = False

# duration of the deepsleep
dsSeconds = 1800  # 30 minutes

# local MQTT broker
localmqttHost = ""

# ThingSpeak configuration from here:
# https://de.mathworks.com/help/thingspeak/use-raspberry-pi-board-that-runs-python-websockets-to-publish-to-a-channel.html
#
# The ThingSpeak Channel ID.
# Replace <YOUR-CHANNEL-ID> with your channel ID.
channelID = b"<YOUR-CHANNEL-ID>"

# The Write API Key for the channel.
# Replace <YOUR-CHANNEL-WRITEAPIKEY> with your write API key.
writeAPIKey = b"<YOUR-CHANNEL-WRITEAPIKEY>"

# The Hostname of the ThingSpeak MQTT broker.
mqttHost = "mqtt.thingspeak.com"

# You can use any Username.
mqttUsername = b"ignore"

# Your MQTT API Key from Account > My Profile.
mqttAPIKey = b"<YOUR-APIKEY>"

def do_connect():
  import network

  # your WLAN credentials
  ssid = ""
  password = ""
 
  station = network.WLAN(network.STA_IF)
  ap = network.WLAN(network.AP_IF)
  if ap.active():
    ap.active(False)  # switch off AP in case it is on
 
  if station.isconnected() == True:
    print("Already connected")
    return

  station.active(True)
  station.connect(ssid, password)
 
  while station.isconnected() == False:
    pass
 
  print("Connection successful")
  print(station.ifconfig())
  

# timeout function for socket
def settimeout(duration): 
  pass
  
def settimeout2(duration): 
  pass

if __name__ == "__main__":
  adc0 = machine.ADC(0)  # create ADC object on ADC pin

  rtc = machine.RTC()
  rtc.irq(trigger=rtc.ALARM0, wake=machine.DEEPSLEEP)  # create an irq object triggered by a real time clock alarm

  if machine.reset_cause() == machine.DEEPSLEEP_RESET:  # judge the reset cause
    print('woke from a deepsleep')
    
  do_connect()

  localclient = MQTTClient("", localmqttHost, port=1883)
  localclient.settimeout = settimeout
  try:
    localclient.connect()
  except Exception as err:
    print("local exception", err)    

  remoteclient = MQTTClient("somethingrandom341", mqttHost, user=mqttUsername, password=mqttAPIKey)  # port=80 is not working, but 0=1883 is ok
  remoteclient.settimeout = settimeout2
  try:
    remoteclient.connect()
  except Exception as err:
    print("remote exception", err)    

  remotetopic = b"channels/" + channelID + b"/publish/" + writeAPIKey

  while True:
    print("publishing via MQTT")
    payload = str(adc0.read())  # read ADC value
    localclient.publish("test/orchid", payload)  # publish locally
    payload = b"field1=" + payload  # build payload for ThingSpeak
    remoteclient.publish(remotetopic, payload)  # publish to ThingSpeak
    
    time.sleep(5)
    print("deepsleep", dsSeconds, "seconds")
    if not debug:
      rtc.alarm(rtc.ALARM0, dsSeconds * 1000)  # set the RTC alarm
      machine.deepsleep()  # let board deepsleep
      
