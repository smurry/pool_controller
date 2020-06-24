# Pool Controller v3 by Stefan Murry
# main.py
# (C) Copyright Stefan Murry 2020.
# Released under the MIT licence.

# Public brokers https://github.com/smurry/Pool_controller

# This code was written for the ESP32 DEVC from expressif.  Various other versions of this module
# have been tested as well.

# the code below uses asyncio which requires a recent (more recent than May 20, 2020) micropython firmware for the ESP32
# firmware can be downloaded from here: https://micropython.org/download/esp32/

from mqtt_as import MQTTClient, config
from config import wifi_led, blue_led, ph_topic_pub, orp_topic_pub, topic_sub, resp_pub, Sensor, Pump, Temp_sensor
import uasyncio as asyncio
from machine import Pin, RTC, UART, reset
from array import *
import time
import sys
import network

loop = asyncio.get_event_loop()
outages = 0
ph_vals=[] # list to hold ph values
orp_vals=[] # list to hold ORP values
cal_finish=False

# pushing the right button on the ESP32 will exit the program back to REPL
def exit_to_repl(pin):
    client.close()
    blue_led(True)
    sys.exit('Exiting to REPL')

# RSSI is available if your WiFi is broadcasting an SSID.  Doesn't work if
# the SSID is not broadcast.
async def get_rssi():
    global rssi
    s = network.WLAN()
    ssid = config['ssid'].encode('UTF8')
    try:
        rssi = [x[3] for x in s.scan() if x[0] == ssid][0]
    except IndexError:  # ssid not found.
        rssi = -199
    print('RSSI: {}'.format(rssi))
    loop.create_task(client.publish(resp_pub, 'RSSI: {}'.format(rssi), qos = 1))

# Temperature is read from a DS18B20 Temperature sensor.  In principle, many sensors
# can be connected if desired.
async def get_temp():
    try:
        t=Temp_sensor()
        roms=t.scan()
        t.convert_temp()
        await asyncio.sleep(0.75)
        for rom in roms:
            temp=t.read_temp(rom)
            print('rom: {}'.format(rom))
            print('temp: {}'.format(temp))
            loop.create_task(client.publish(resp_pub, 'temp: {}'.format(temp), qos = 1))
    except:
        loop.create_task(client.publish(resp_pub, 'temp sensor error', qos = 1))

async def send_command(u, cmd):
    command_to_send=cmd+'\r'
    resp=u.write(command_to_send)
    print('Received response: {}'.format(resp))
    return resp

# in addition to providing the latest pH and ORP values, the program will provide
# a moving average value.  Averaging window is defined in the config.txt file
def moving_average(a, v, w): # an existing list of values, a new value, and an averaging window
    a.append(v) # add new value to the list
    if len(a)>w:
        a.pop(0) # if the new list is longer than the window, then pop the oldest item
    avg=sum(a)/len(a) # average the new list
    return(a, avg)

async def read_response(u):
    try:
        r=u.read().decode("utf-8")
        print('response: {}'.format(r))
    except:
        print('{} timeout'.format(u))
        r='8.888' + '\r' # in case of a timeout, send a default 8.888 pH value
    return r


async def read_ph(u):
     await send_command(u, 'R')
     await asyncio.sleep(1)
     reading = await read_response(u)
     ph=float(reading.split('\r')[0])
     return ph

async def read_orp(u):
     await send_command(u, 'R')
     await asyncio.sleep(1)
     reading = await read_response(u)
     orp=float(reading.split('\r')[0])
     return orp


async def pulse():  # This demo pulses blue LED each time a subscribed msg arrives.
    blue_led(True)
    await asyncio.sleep(0.5)
    blue_led(False)
    await asyncio.sleep(0.5)
    return True

async def turn_on_pump(pump, on_time):
    if pump == Pump.PH_PUMP:
        print('turning on pump {}'.format(pump))
        Pump.pump_1_pin.on()
        asyncio.create_task(client.publish(resp_pub, 'ph:on', qos = 1))
        w = await (asyncio.sleep(on_time))
        print('turning off pump {}'.format(pump))
        Pump.pump_1_pin.off()
        asyncio.create_task(client.publish(resp_pub, 'ph:off', qos = 1))
    elif pump == Pump.ORP_PUMP:
        print('turning on pump {}'.format(pump))
        Pump.pump_2_pin.on()
        asyncio.create_task(client.publish(resp_pub, 'orp:on', qos = 1))
        w = await (asyncio.sleep(on_time))
        print('turning off pump {}'.format(pump))
        Pump.pump_2_pin.off()
        asyncio.create_task(client.publish(resp_pub, 'orp:off', qos = 1))

    return True

async def turn_off_pump(pump, nothing):
    if pump==Pump.PH_PUMP:
        print('turning off pump {}'.format(pump))
        Pump.pump_1_pin.off()
        await client.publish(resp_pub, 'ph:off', qos = 1)
    elif pump == Pump.ORP_PUMP:
        print('turning off pump {}'.format(pump))
        Pump.pump_1_pin.off()
        await client.publish(resp_pub, 'orp:off', qos = 1)
    return True

async def calibrate(sensor, interval, timeout=300):
    global cal_finish
    global ph_uart
    global orp_uart

    cal_start=time.time()
    print('cal_start: {}'.format(cal_start))
    await client.publish(resp_pub, 'cal:{}:start'.format(sensor), qos = 1)
    while True:
        if sensor==1:
            ph=await read_ph(ph_uart)
            print("Ph: {}".format(ph))
            await client.publish(ph_topic_pub, '{}'.format(ph), qos = 1)
        elif sensor==2:
            orp=await read_orp(orp_uart)
            print("ORP: {}".format(orp))
            await client.publish(orp_topic_pub, '{}'.format(orp), qos = 1)
        await asyncio.sleep(interval)
        print('time now: {}'.format(time.time()))
        if cal_finish:
            if sensor == 1:
                print('issuing Ph cal mid command')
                await send_command(ph_uart,'Cal,mid,7.00')
            elif sensor == 2:
                print('issuing ORP cal command')
                await send_command(ph_uart,'cal,225')
            print('Calibration Finished')
            await client.publish(resp_pub, 'cal:{}:end'.format(sensor), qos = 1)
            cal_finish=False
            return True
        if time.time()-cal_start > timeout:
            print('end_time: {}'.format(time.time()))
            await client.publish(resp_pub, 'cal:{}:timeout'.format(sensor), qos = 1)
            return False

async def check_cal_finish(void1,void2):
    global cal_finish
    cal_finish=True
    return True


async def unknown_command():
    print('Unknown command received, ignoring')
    return False

# callback to process incoming commands received over MQTT
def sub_cb(topic, msg, retained):
    global commands
    print('in sub_cb')
    #message format: ph:on:30
    message=msg.decode().lower()
    loop.create_task(pulse())
    print('topic: {}, msg: {}'.format(topic, message))
    if message == 'status':
        loop.create_task(get_rssi())
        loop.create_task(pulse())
        loop.create_task(pulse())
        loop.create_task(get_temp())
        loop.create_task(pulse())
        loop.create_task(pulse())

    else:
        try:
            print('trying')
            msg_split=message.split(':')
            cmd=commands.get(msg_split[1], unknown_command)
        except:
            cmd='unknown'
            print('Unknown command received, ignoring')
            loop.create_task(client.publish(resp_pub, 'unknown command', qos = 1))
        print('received command: {}'.format(cmd))

        if msg_split[0]=='ph': # MQTT command string starts with ph:
            try:
                command_arg=msg_split[2]
            except:
                command_arg='0'
            print('About to execute ph command')
            loop.create_task(cmd(Pump.PH_PUMP,int(command_arg)))

        if msg_split[0]=='orp': # MQTT command string starts with orp:
            try:
                command_arg=msg_split[2]
            except:
                command_arg='0'
            print('About to execute orp command')
            loop.create_task(cmd(Pump.ORP_PUMP,int(command_arg)))

async def wifi_han(state):
    global outages
    wifi_led(not state)  # Light LED when WiFi up
    if state:
        print('We are connected to broker.')
    else:
        outages += 1
        print('WiFi or broker is down.')
    await asyncio.sleep(1)

async def conn_han(client):
    await client.subscribe(topic_sub, 1)

async def main(client):
    global ph_vals
    global orp_vals
    global ph_uart
    global orp_uart
    try:
        await client.connect()
    except OSError:
        print('Connection failed.')
        await asyncio.sleep(5)
        reset()
    n = 0
    try:
        ph_uart=UART(Sensor.ph_uart_port, tx=Sensor.ph_tx, rx=Sensor.ph_rx)
        ph_uart.init(9600, bits=8, parity=None, stop=1)
    except OSError:
        print('Ph UART failed.')
        return
    try:
        orp_uart=UART(Sensor.orp_uart_port, tx=Sensor.orp_tx, rx=Sensor.orp_rx)
        orp_uart.init(9600, bits=8, parity=None, stop=1)
    except OSError:
        print('orp UART failed.')
        return
    await client.publish(resp_pub, 'online', qos = 1)
    await asyncio.sleep(5)
    while True:
        ma=()
        print('publish', n)
        # If WiFi is down the following will pause for the duration.
        ph=await read_ph(ph_uart)
        print("Ph: {}".format(ph))
        await client.publish(ph_topic_pub, '{}'.format(ph), qos = 1)
        print('ph_vals: {}'.format(ph_vals))
        print('ph: {}'.format(ph))
        print('ma_window: {}'.format(Sensor.ph_ma_window))
        ma=moving_average(ph_vals, float(ph), Sensor.ph_ma_window)
        await client.publish(ph_topic_pub + '/moving_average', '{}'.format(ma[1]), qos = 1)
        ph_vals=ma[0]
        orp=await read_orp(orp_uart)
        print("ORP: {}".format(orp))
        await client.publish(orp_topic_pub, '{}'.format(orp), qos = 1)
        ma=moving_average(orp_vals, float(orp), Sensor.orp_ma_window)
        await client.publish(orp_topic_pub + '/moving_average', '{}'.format(ma[1]), qos = 1)
        orp_vals=ma[0]
        await asyncio.sleep(Sensor.report_interval)
        n += 1

# Define configuration
config['subs_cb'] = sub_cb # defines the coroutine to run if a message is received
config['wifi_coro'] = wifi_han # handler for change in wifi connection status
config['will'] = (topic_sub, 'offline', False, 0)  # last will
config['connect_coro'] = conn_han # handler for successful connection to MQTT broker
print('ph_pump: {}'.format(Pump.PH_PUMP))
print('orp_pump: {}'.format(Pump.ORP_PUMP))
# the below dictionary defines the coroutines to be run in the event the command defined
# by the dictionary key is received.
commands = {
    'on': turn_on_pump,
    'off': turn_off_pump,
    'cal': calibrate,
    'done': check_cal_finish
}

# Set up client. Enable optional debug statements.
MQTTClient.DEBUG = True
client = MQTTClient(config)
Sensor.repl_button.irq(trigger=Pin.IRQ_FALLING, handler=exit_to_repl)

try:
    loop.run_until_complete(main(client))
finally:  # Prevent LmacRxBlk:1 errors.
    client.close()
    blue_led(True)
