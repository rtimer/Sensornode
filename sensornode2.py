# sensornode2.py
#
# MQTT client for ESP8266 w/ MicroPython & deepsleep mode
# supports analog and capacitive humidity sensors, sends data locally and to cloud brokers (currently ThingSpeak)
# - to measure 400 kHz frequency assembler routines are used to read ESP8266s CCOUNT which has a resolution of 12,5ns
#
# 02-03/18 HSN

import gc
import esp
from flashbdev import bdev
import machine, time
from umqtt import MQTTClient
import dht

# set to True for skipping deepsleep & sending to the cloud
debug = False

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

# WLAN credentials
ssid = ""
password = ""

# duration of the deepsleep
dsSeconds = 3600  # 60 minutes
# port for sensor power
sensor_analogpowerpin = const(13)  # GPIO13 = D7
sensor_digitalpowerpin = const(15)  # GPIO15 = D8
sensor_digitalinputpin = const(14)  # GPIO14 = D5

# this is the xtensa port for GPIO input
GPIO_IN = const(0x60000318)

# connect to WLAN and switch off AP when necessary
def do_connect():
  import network

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

# fun with machine code: read 10 cycles of digital input, return number of processor ticks in a2
# registers: a3=loop count, a4=loop decrement, a5, a6=port input, a7=pin bitmask, a10=port address, a11=ccount initial value
# would be fast enough to measure frequencies about 1 MHz
@micropython.asm_xtensa
def count_ticks() -> uint:
  #data(3, 0x2aa022) # example for data function: movi a2, 42 -> loads 42 to a2, works!
  movi(a4, 1) # loop decrement
  movi(a7, sensor_digitalinputpin) # pin bit mask
  movi(a10, GPIO_IN) # GPIO base address for input
  
  label(loop_start)
  l16ui(a6, a10, 0)  # load GPIO input before first run
  bbs(a6, a7, loop_start)  # wait until port bit is initially 0
  movi(a3, 10)  # loop count
  # start measurement
  data(3, 0x03eab0)  # rsr a11, ccount -> read special register cccount (234); register no. 11 is encoded in nibble 4
  label(loop_wait1)
  l16ui(a6, a10, 0)  # load GPIO input
  bbc(a6, a7, loop_wait1)  # wait until port bit is 1
  label(loop_wait0)
  l16ui(a6, a10, 0)  # load GPIO input
  bbs(a6, a7, loop_wait0)  # wait until port bit is 0
  sub(a3, a3, a4)  # decrement counter
  bnez(a3, loop_wait1)
  data(3, 0x03ea60)  # rsr a6, ccount
  # end measurement
  blt(a6, a11, loop_start)  # check for ccount overflow, as this will happen every 53,6s @80 MHz
  sub(a2, a6, a11)  # delta in clock ticks

if __name__ == "__main__":
  sensor_digitalpower = machine.Pin(sensor_digitalpowerpin, machine.Pin.OUT)
  sensor_analogpower = machine.Pin(sensor_analogpowerpin, machine.Pin.OUT)
  sensor_digitalpower.off()
  sensor_analogpower.off()
  sensor_digital = machine.Pin(sensor_digitalinputpin, machine.Pin.IN)
  adc0 = machine.ADC(0)  # create ADC object analog input (adcmode 0)

  rtc = machine.RTC()
  rtc.irq(trigger=rtc.ALARM0, wake=machine.DEEPSLEEP)  # create an irq object triggered by a real time clock alarm
  if machine.reset_cause() == machine.DEEPSLEEP_RESET:  # judge the reset cause
    print('woke from a deepsleep')
  do_connect()

  time.sleep(5)  # wait a little to stabilize
  print("Start")
  localclient = MQTTClient("", localmqttHost, port=1883)
  localclient.settimeout = settimeout
  try:
    localclient.connect()
  except Exception as err:
    print("local exception", err)

  if not debug:
    remoteclient = MQTTClient("deadbeef0304", mqttHost, user=mqttUsername, password=mqttAPIKey)  # port=80 is not working, but 0=1883 (default) is ok
    remoteclient.settimeout = settimeout
    try:
      remoteclient.connect()
    except Exception as err:
      print("remote exception", err)    
    remotetopic = b"channels/" + channelID + b"/publish/" + writeAPIKey  # build topic for ThingSpeak
    dhtSensor = dht.DHT11(machine.Pin(2))  # DHT11 shield
  
  while True:  # will usually only be checked once due to deep sleep
    sensor_digitalpower.on() # now give some power to the digital sensor
    time.sleep(1)  # necessary!
    if not debug:
      dhtSensor.measure()
      
    gc.disable()  # pause garbage collection
    ticks = count_ticks() / 10
    digital_freq = int(1 / (ticks * 0.0000125))  # calculate frequency in kHz
    print(ticks * 12.5, "ns =", ticks * 12.5/1000, "us ~ ", digital_freq, "kHz")
    gc.enable()
    sensor_digitalpower.off() # save energy

    sensor_analogpower.on()
    time.sleep(2)
    print("publishing via MQTT")
    payload = b"field1=" + str(adc0.read())  # read analog sensor value from ADC0
    payload += b"&field4=" + str(digital_freq)
    if not debug:
      payload = payload + b"&field2=" + str(dhtSensor.temperature()) + b"&field3=" + str(dhtSensor.humidity())
    localclient.publish("test/value", payload)  # publish locally
    time.sleep(5)  # keep board online for 5 seconds
    if not debug:
      localclient.disconnect()

    sensor_analogpower.off()
    if not debug:
      print("deepsleep", dsSeconds, "seconds")
      remoteclient.publish(remotetopic, payload)  # publish to ThingSpeak
      remoteclient.disconnect()
      rtc.alarm(rtc.ALARM0, dsSeconds * 1000)  # set the RTC alarm
      machine.deepsleep()  # let board deepsleep
