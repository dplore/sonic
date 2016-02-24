#!/usr/bin/env python
#
# Copyright (C) 2016 Arista Networks, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
from collections import namedtuple

# scd PCI address
scd_address = "0000:04:00.0"

# Data structures for holding mappings of hardware addresses to
# software functionality
resets = {
   0x4000 : [
      (0, "t2_reset"),
      (2, "phy1_reset"),
      (3, "phy2_reset"),
      (4, "phy3_reset"),
      (5, "phy4_reset"),
      ],
   }

smbus_masters = range(0x8000, 0x8400 + 1, 0x100)

leds = [
   (0x6050, "status"),
   (0x6060, "fan_status"),
   (0x6070, "psu1"),
   (0x6080, "psu2"),
   (0x6090, "beacon"),
   ]

addr = 0x6100
for i in range(1, 24 + 1):
   for j in range(1, 4 + 1):
      leds.append((addr, "qsfp%d_%d" % (i, j)))
      addr += 0x10

addr = 0x6720
for i in range(25, 32 + 1):
   leds.append((addr, "qsfp%d" % i))
   if i % 2:
      addr += 0x30
   else:
      addr += 0x50

Gpio = namedtuple("Gpio", ["addr", "name", "ro", "activeLow"])
sb_gpios = []
sb_leds = []
num_sb_fans = 4
for i in range(num_sb_fans):
   fan_id = i + 1
   sb_gpios.append(Gpio(203 + (6 * i), "fan%d_id0" % fan_id, True, False))
   sb_gpios.append(Gpio(204 + (6 * i), "fan%d_id1" % fan_id, True, False))
   sb_gpios.append(Gpio(205 + (6 * i), "fan%d_id2" % fan_id, True, False))
   sb_gpios.append(Gpio(206 + (6 * i), "fan%d_present" % fan_id, True, True))
   sb_leds.append((207 + (6 * i), "fan%d_led" % fan_id))

scd_gpios = {
   0x5000 : [
      Gpio(0, "psu1_present", True, False),
      Gpio(1, "psu2_present", True, False),
      ],
}

addr = 0x5010
for i in range(1, 32 + 1):
   scd_gpios[addr] = [
      Gpio(0, "qsfp%d_interrupt" % i, True, True),
      Gpio(2, "qsfp%d_present" % i, True, True),
      Gpio(3, "qsfp%d_interrupt_changed" % i, True, False),
      Gpio(5, "qsfp%d_present_changed" % i, True, False),
      Gpio(6, "qsfp%d_lp_mode" % i, False, False),
      Gpio(7, "qsfp%d_reset" % i, False, False),
      Gpio(8, "qsfp%d_modsel" % i, False, True),
      ]
   addr += 0x10

# Process hardware mappings into separate lists so we can manipulate
# them conveniently
reset_addrs = sorted(resets)
reset_names = []
reset_masks = []

for addr in reset_addrs:
   mask = 0
   (bits, names) = zip(*resets[addr])
   reset_names.extend(names)
   for bit in bits:
      mask |= (1 << bit)
   reset_masks.append(mask)

(led_addrs, led_names) = zip(*leds)
(sb_gpios, sb_gpio_names, sb_gpios_ro, sb_gpios_active_low) = zip(*sb_gpios)
(sb_leds, sb_led_names) = zip(*sb_leds)

gpio_addrs = sorted(scd_gpios)
gpio_names = []
gpio_masks = []
gpio_ro = []
gpio_active_low = []
for addr in gpio_addrs:
   mask = 0
   ro_mask = 0
   active_low_mask = 0
   for (bit, name, ro, active_low) in scd_gpios[addr]:
      gpio_names.append(name)
      mask |= (1 << bit)
      if ro:
         ro_mask |= (1 << bit)
      if active_low:
         active_low_mask |= (1 << bit)
   gpio_masks.append(mask)
   gpio_ro.append(ro_mask)
   gpio_active_low.append(active_low_mask)

# Generate comma-separated strings in the right format from the lists
# above to be written to sysfs
def formatHex( x ):
   return "0x%08x" % x

def formatDec( x ):
   return "%d" % x

reset_addrs = ",".join(map(formatHex, reset_addrs))
reset_names = ",".join(reset_names)
reset_masks = ",".join(map(formatHex, reset_masks))

master_addrs = ",".join(map(formatHex, smbus_masters))

led_addrs = ",".join(map(formatHex, led_addrs))
led_names = ",".join(led_names)

sb_gpios = ",".join(map(str, sb_gpios))
sb_gpio_names = ",".join(sb_gpio_names)
sb_gpios_ro = ",".join(map(formatDec, sb_gpios_ro))
sb_gpios_active_low = ",".join(map(formatDec, sb_gpios_active_low))

gpio_addrs = ",".join(map(formatHex, gpio_addrs))
gpio_masks = ",".join(map(formatHex, gpio_masks))
gpio_names = ",".join(gpio_names)
gpio_ro = ",".join(map(formatHex, gpio_ro))
gpio_active_low = ",".join(map(formatHex, gpio_active_low))

sb_leds = ",".join(map(str, sb_leds))
sb_led_names = ",".join(sb_led_names)

init_trigger = 1

# Install and initialize scd driver
os.system("modprobe scd")
os.chdir("/sys/bus/pci/drivers/scd/%s" % scd_address)

for fname in [
   "reset_addrs", "reset_names", "reset_masks",
   "master_addrs",
   "led_addrs", "led_names",
   "sb_gpios", "sb_gpio_names", "sb_gpios_ro", "sb_gpios_active_low",
   "gpio_addrs", "gpio_masks", "gpio_names", "gpio_ro", "gpio_active_low",
   "num_sb_fans",
   "sb_leds", "sb_led_names",
   "init_trigger", # Must always be last
   ]:
   with open(fname, "w") as f:
      f.write(str(eval(fname)))

# Temperature sensors
os.system("modprobe lm73")
os.system("modprobe lm90")

# PMBus devices
for (bus, addr) in [
   (3, 0x4e),
   (5, 0x58),
   (6, 0x58),
   (7, 0x4e),
   ]:
   with open("/sys/bus/i2c/devices/i2c-%d/new_device" % bus, "w") as f:
      f.write("pmbus 0x%02x" % addr)

# EEPROM
os.system("modprobe eeprom")

# QSFP+
bus = 10
addr = 0x50
for i in range(32):
   with open("/sys/bus/i2c/devices/i2c-%d/new_device" % bus, "w") as f:
      f.write("sff8436 0x%02x" % addr)
   bus += 1

# Take QSFPs out of reset and assert modsel
for i in range(1, 32 + 1):
   with open("qsfp%d_reset/direction" % i, "w") as f:
      f.write("out")
   with open("qsfp%d_reset/value" % i, "w") as f:
      f.write("0")
   with open("qsfp%d_modsel/direction" % i, "w") as f:
      f.write("out")
   with open("qsfp%d_modsel/value" % i, "w") as f:
      f.write("1")
