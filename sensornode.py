# sensornode.py
#
# MQTT client for ESP8266 w/ MicroPython & deepsleep mode
#
# 02/18 HSN

import machine, time
from umqtt import MQTTClient

debug = False  # no depsleep

def do_connect():
  import network

  ssid = "_your_SSID_here_"
  password =  "_your_wlan_password_here_"
 
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
  
def settimeout(duration): 
  pass

if __name__ == "__main__":

  adc0 = machine.ADC(0)  # create ADC object on ADC pin

  rtc = machine.RTC()
  rtc.irq(trigger=rtc.ALARM0, wake=machine.DEEPSLEEP)  # create an irq object triggered by a real time clock alarm

  if machine.reset_cause() == machine.DEEPSLEEP_RESET:  # judge the reset cause
    print('woke from a deepsleep')
    
  do_connect()

  client = MQTTClient("_your_mqtt_user_here_", "_your_mqtt_broker_here_", port=1883)
  client.settimeout = settimeout
  client.connect()

  while True:
    print("Sending ON")
    client.publish("test/value", str(adc0.read()))
    time.sleep(5)
    print("deepsleep 1800 seconds")
    rtc.alarm(rtc.ALARM0, 1800000)  # set the RTC alarm for 30 minutes
    if not debug:
      machine.deepsleep()  # let board deepsleep

