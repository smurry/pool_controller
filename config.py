# config.py Local configuration for pool controller v3
from sys import platform
from mqtt_as import config
import json
import ubinascii
import machine, onewire, ds18x20


# Load configuration from file
with open (r'conf.txt', 'rt') as File_object:     # Open conf.txt for reading text
    conf = File_object.read()                   # Read the entire file into a variable

d = json.loads(conf)

# Set up config variables
topic_sub = d['topic_sub'].encode('utf-8')
ph_topic_pub = d['ph_topic_pub'].encode('utf-8')
orp_topic_pub = d['orp_topic_pub'].encode('utf-8')
resp_pub = d['resp_pub'].encode('utf-8')
report_interval = int(d['report_interval'])

config['server'] = d['mqtt_server']  # MQTT Broker Address
config['port'] = int(d['mqtt_port']) #MQTT Broker Port
config['user'] = d['mqtt_username'] # MQTT Broker Username
config['password'] = d['mqtt_pw'] #MQTT Broker Password
config['ssid'] = d['ssid'] #WiFi SSID
config['wifi_pw'] = d['password'] # Wifi Password
config['keepalive'] = int(d['keepalive_interval'])
config['hostname'] = d['hostname'] # configure human-readable Wifi hostname

class Sensor:
    with open (r'conf.txt', 'rt') as File_object:     # Open conf.txt for reading text
        conf = File_object.read()                   # Read the entire file into a variable

    global d
    d = json.loads(conf)

    ph_uart_port=int(d['ph_uart_port']) # UART port on the ESP32 used for the PH sensor
    ph_tx = int(d['ph_tx']) # PH sensor Tx pin
    ph_rx = int(d['ph_rx']) # PH sensor Rx pin
    orp_uart_port=int(d['orp_uart_port']) # UART port on the ESP32 used for the ORP sensor
    orp_tx = int(d['orp_tx']) # ORP sensor Tx pin
    orp_rx = int(d['orp_rx']) # ORP sensor Rx pin
    repl_button = machine.Pin(0, machine.Pin.IN, machine.Pin.PULL_UP) #define a button which will exit the program
    report_interval = int(d['report_interval']) # how often are Ph and ORP values sent over MQTT (sec)
    ph_ma_window = int(d['ph_ma_window']) # how many datapoints in the moving average window
    orp_ma_window = int(d['orp_ma_window'])

class Pump:
    global d
    pump_1_pin=machine.Pin(int(d['pump_1_pin']), machine.Pin.OUT)
    pump_2_pin=machine.Pin(int(d['pump_2_pin']), machine.Pin.OUT)
    PH_PUMP = int(d['ph_pump'])
    ORP_PUMP = int(d['orp_pump'])

class Temp_sensor():
    global d
    def __init__(self):
        self.ds_pin = machine.Pin(int(d['ds_pin']))
        self.ds_sensor = ds18x20.DS18X20(onewire.OneWire(self.ds_pin))

    def scan(self):
        roms=self.ds_sensor.scan()
        print('Found DS devices: {}'.format(roms))
        return roms

    def convert_temp(self):
        c=self.ds_sensor.convert_temp()
        print(c)
        return c

    def read_temp(self, rom):
        c = self.ds_sensor.read_temp(rom)
        print(c)
        return c




# I haven't tested with platforms other than ESP32, but the following pin definitions for the LEDs
# are known to vary across the different platforms.

if platform == 'esp8266' or platform == 'esp32' or platform == 'esp32_LoBo':
    from machine import Pin
    def ledfunc(pin):
        pin = pin
        def func(v):
            pin(not v)  # Active low on ESP8266
        return func
    wifi_led = ledfunc(Pin(26, Pin.OUT, value = 0))  # Red LED for connected to broker
    blue_led = ledfunc(Pin(2, Pin.OUT, value = 1))  # WiFi connected or message received
elif platform == 'pyboard':
    from pyb import LED
    def ledfunc(led, init):
        led = led
        led.on() if init else led.off()
        def func(v):
            led.on() if v else led.off()
        return func
    wifi_led = ledfunc(LED(1), 1)
    blue_led = ledfunc(LED(3), 0)
