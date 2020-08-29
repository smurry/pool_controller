"""
Currently in git version control v0.1 branch.

Zone Controller for irrigation system.  Designed to be run on an ESP32 controller.

Listens for incoming MQTT commands, formatted as follows:

    {command}:zone:time

for example: 'water:1:5' would open the zone 1 vale for 5 minutes.
similarly, 'water:2:10' would open the zone 2 valve for 10 minutes.

Basic program flow:

Create a class called zone, which has attributes zone_id, active and methods like turn_on and turn_off

"""

import machine
from machine import Pin, RTC
import time
from robust import MQTTClient
import json
import ubinascii

# Load configuration from file
with open (r'conf.txt', 'rt') as File_object:     # Open conf.txt for reading text
    config = File_object.read()                   # Read the entire file into a variable

d = json.loads(config)

#print(d)

mqtt_server = d['mqtt_server']
topic_sub = d['topic_sub'].encode('utf-8')
topic_pub = d['topic_pub'].encode('utf-8')
zones = d['zones']
keepalive_interval = int(d['keepalive_interval'])
mqtt_pw = d['mqtt_pw']
mqtt_username = d['mqtt_username']

print('server: {},Sub topic: {}, Pub Topic: {}'.format(mqtt_server, topic_sub, topic_pub))
zone_count = len(d['zones'])

#print('zones: {}'.format(zones))

# create a command stack.  This stack will be a list of lists containing the commands received and their arguments
# for example, [[water:1:5]] would be a command to water zone 1 for 5 minutes.
c_stack = []
stop_now = False
lastping = 0
#print('just before rtc')
#rtc = RTC()
d=RTC().datetime()
res = "{}-{:02}-{:02} {}:{}:{}".format(str(d[0])[2:], d[1], d[2], d[4], d[5], d[6])
#print('Just got RTC at: %s' %res)

client_id = ubinascii.hexlify(machine.unique_id())

def exit_handler():
    print("Application Ending.")
    pub("Disconnecting")
    client.disconnect()
    raise

def get_last_cmd(ls):
  if ls != []:
    c = ls[len(ls)-1][0]
    return c
  return []

def format_now():
  d=RTC().datetime()
  res = "{}-{:02}-{:02} {:02}:{:02}:{:02}".format(str(d[0])[2:], d[1], d[2], d[4], d[5], d[6])
  return(res)

def pull_cmd(ls):
    ls.reverse()
    elem = ls.pop()
    ls.reverse()
    a = elem[0]
    b = int(elem[1])
    c = int(elem[2])
    return a,b,c


def sub_cb(topic, msg):
  # whenever there is a new message posted, check the topic.  If it is a command to the controller, then check if it is a stop command.
  # Flag a stop command to be dealt with immediately.  Otherwise, throw the command onto the stack.
  global c_stack, stop_now, topic_sub
  #print((topic, msg))
  if topic == topic_sub:
    #print('Received command: %s' %msg)
    new_string=str(msg, 'utf-8')
    #print('Received command: %s' %new_string)
    new_msg = new_string.split(':')
    #print(new_msg)
    # TODO: move this next part to its own method.  Something like check_special to look for commands that need
    # to be processed immediately (not added to the back of the queue).  Add a "status" special command to get
    # current zone status.
    if new_msg[0] == 'stop':
        stop_now = True
        return
    else: c_stack.append(new_msg)
    #print(c_stack)
    return

def pub(msg):
  global client_id, mqtt_server, topic_pub
  client.publish(topic_pub, msg.encode('utf-8'))

def connect_and_subscribe():
  global client_id, mqtt_server, topic_sub, mqtt_pw, mqtt_username
  client = MQTTClient(client_id, mqtt_server, 0, mqtt_username, mqtt_pw, keepalive_interval, False, {})
  print('About to try to connect to %s MQTT broker, subscribed to %s password %s username' % (mqtt_server, mqtt_pw, mqtt_username))
  client.DEBUG = True
  client.set_callback(sub_cb)
  if not client.connect(clean_session=False):
    print("New session being set up")
    client.subscribe(topic_sub)
  else:
    print('do not set up new session, reconnect to existing one...')
    client.subscribe(topic_sub)
  print('Connected to %s MQTT broker, subscribed to %s topic' % (mqtt_server, topic_sub))
  return client

def restart_and_reconnect():
  print('Failed to connect to MQTT broker. Reconnecting...')
  time.sleep(5)
  machine.reset()

def is_connected():
  station = network.WLAN(network.STA_IF)
  #print('IP Address: %s' %station.ifconfig()[0])
  b=station.ifconfig()[0][0]
  #print(b)
  if b == '0': return False
  else: return True

def keepalive_check(tm):
    now = time.time()
    if (now - tm) > keepalive_interval:
        client.ping()
        print('Sent ping at {}'.format(now))
        return now
    else: return tm

class Zone:

    def __init__(self,zone_id,st,active = True):
        """

        :param zone_id: zone ID (number)
        :param active: Boolean, whether zone is active or not
        :param st: Boolean, zone is currently on/off
        """
        self.zone_id=zone_id
        self.active=active
        self.st=st

    def turn_on(self):
        if self.active:
            valve[self.zone_id].on()
            print('valve {} on'.format(self.zone_id))
            self.st=True
        else:
            print('zone not active.  cannot turn on')

    def turn_off(self):
        if self.active:
            valve[self.zone_id].off()
            print('valve {} off'.format(self.zone_id))
            self.st=False
        else:
            print('zone not active.  cannot turn off.')


#class Controller:
#    def __init__(self):
        """
        :param stack: Command stack
        """
#        self.stack=stack

#print('entering main')
try:
 now_dt = format_now()
 print('Successful Boot at: %s' %now_dt)
 client = connect_and_subscribe()
 pub(now_dt)

except OSError as e:
  print("OS error: {0}".format(e))
  restart_and_reconnect()


#instantiate a controller and zones

valve = []
#c = Controller()
valve.insert(0, Pin(2, Pin.OUT))
blue_led = valve[0]
for i in range(1, (zone_count+1)):
    valve.insert(i, Pin(int(zones['zone{}'.format(i)]),Pin.OUT))

for i in range(zone_count+1):
    print('valve{}: {}'.format(i,valve[i]))


#instantiate zones:
zone = []
zone.insert(0, Zone(0,False,True))
for i in range(1, zone_count+1):
    zone.insert(i, Zone(i,False,True))
    #print('zone: {}'.format(zone[i]))

watering = False

while True:
    try:
        # check for incoming MQTT message. If the last message received is a stop command, then shut stuff off
        # check if there is a connection to the MQTT server.  If so, check for a message
        is_message = client.check_msg()
        # if is_message is "Error" then we are not connected to the MQTT server.  First, check whether the internet is connected
        # if internet is connected, then try to reconnect to the MQTT server.
        if is_message == 'Error':
          print('is_message: {}'.format(is_message))
          print('Error connecting to MQTT server.  Attempting reconnect')
          print('Connection Status: {}'.format(is_connected()))
          if is_connected():
              client.reconnect()
              lastping = time.time()
          else: pass
        lastping = keepalive_check(lastping)

       # at this point, there is no internet connection, so keep running the try loop here to see if the timer has expired and the
       # water needs to be shut off.  Then loop again and see if the internet and MQTT servers can be reconnected

        #print('MQTT: %s' %is_message)
        #print('Type: %s' %type(is_message))

        time.sleep(1)
        # check for incoming MQTT message. If the last message received is a stop command, then shut stuff off
        if stop_now:
          print('Shutting down all zones.')
          mes = ''
          for i in range(0, zone_count+1):
              zone[i].turn_off()
              mes = mes + 'zone{}:{}'.format(i,zone[i].st) + ','
          mes = mes.rstrip(',')
          print(mes)
          pub(mes)
          watering = False
          #if everything is stopped, clear the command stack
          c_stack = []
          now_dt = format_now()
          stop_now = False

          # if already watering, then skip opening valves, otherwise if there's a command waiting, start watering
        if (c_stack != [] and (not watering)):
            c_stack.reverse()
            comm=c_stack.pop()
            c_stack.reverse()
            if comm[0] == 'water':
                zone[int(comm[1])].turn_on()
                start_time=time.time()
                watering = True

            t=float(comm[2])
            d=RTC().datetime()
            res = "{}-{}-{} {}:{}:{}".format(str(d[0])[2:], d[1], d[2], d[4], d[5], d[6])
            print('opening valve%s for %f minutes, starting at %s' %(comm[1], t, res))
            mes = ''
            for i in range(0, zone_count+1):
                    mes = mes + 'zone{}:{}'.format(i,zone[i].st) + ','
            mes = mes.rstrip(',')
            print(mes)
            pub(mes)

        if watering:
            if ((time.time()-start_time) >= (t*60)):
                mes = ''
                print('time up.  Stopping water at: %f' %time.time())
                watering = False
                for i in range(0, zone_count+1):
                    zone[i].turn_off()
                    mes = mes + 'zone{}:{}'.format(i,zone[i].st) + ','
                mes = mes.rstrip(',')
                print(mes)
                pub(mes)

    except OSError as e:
        print("OS error: {0}".format(e))
        #client.disconnect()
        restart_and_reconnect()

    except KeyboardInterrupt as e:
        exit_handler()

