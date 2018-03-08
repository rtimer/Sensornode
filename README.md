# Sensornode
a MicoPython-Script to send analog sensor data with an Wemos D1 mini pro (ESP8266) to a local or cloud MQTT brokers

Uses deepsleep to save energy, you have to connect D0 and RST to allow to wake itself up. Connect A0 with analog input source, D5 with a capacitive sensor and configure WLAN- and MQTT-credentials appropriate.

This has been tested with a Wemos DHT12 and a Battery shield, connected to a 18650 cell. Seems to eat up about 700mAh per week, a 3200 mAh cell could last 4 weeks (not tested yet).

New in version 2:
- some assembler code to enable micropython to read pulse signals up to 400 kHz, without this code you would get stuck with 3 kHz
- code for DHT12 included
- sends the data in the following string: test/value field1=507&field4=253&field2=19&field3=46
- field1=ADC value, field2=temperature, field3=humidity, field4=pulse frequency in kHz
