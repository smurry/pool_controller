# Pool Controller
PH and ORP monitor/control for ESP32

To use, you'll need to flash an ESP32 module with micropython.  See: https://micropython.org/download/esp32/.  Version must be May 20,2020 or later.

You must update the conf-example.sample file:
  1)  edit wifi information and mqtt server information as noted in the file.  All values need to be in quotation marks as in the example file.
  2)  save the file with exactly this filename: conf.txt

After saving the conf.txt file, upload conf.txt, config.py, mqtt_as.py and main.py to the ESP32.  If you are unfamiliar with how to do this, check out https://github.com/BetaRavener/uPyLoader

The sensors configured in the conf.txt file represent IO ports on the ESP32-DEVKITC board.  They are designed to work with isolated carrier boards from Atlas Scientific (for example https://www.atlas-scientific.com/carrier-boards/electrically-isolated-ezo-carrier-board-gen-2/).  You will need to purcahse the carrier boards, EZO modules, and probes from Atlas.

Outputs are provided on the IO ports noted in the conf.txt file for Ph Pump (i.e. acid) and ORP Pump (i.e. bleach).  These pins can be connected through appropriate isolation and relays to peristaltic pumps used to dispense the required chemicals into the pool.

This system was designed to work with Home Assistant, although in principle any MQTT-enabled controller should work.  Configuration files for Home Assistant are in the directory "Home Assistant."  The .yaml package goes into your packages directory and the pool_fc.py is an appdaemon file and should go in the appropriate appdaemon folder.
