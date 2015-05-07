'''
+ write interface
avrdude -c avrispmkII -P usb -p m16u2 -U lfuse:w:0xEF:m -U hfuse:w:0xD9:m -U efuse:w:0xF4:m -U flash:w:interface.hex

+ write booloader
avrdude -c avrispmkII -P usb -p m328p -U lfuse:w:0xFF:m -U hfuse:w:0xDA:m -U efuse:w:0x05:m -U flash:w:bootloader.hex

+ write program
avrdude -c arduino -P {COMx} -b 115200 -p m328p -D -U flash:w:program.hex
'''

import subprocess
import shlex
import time
from serial.tools import list_ports
from time import sleep

AVRDUDE = 'external/avrdude'

INTERFACE  = 'firmware/seeeduino_v4_interface.hex'
BOOTLOADER = 'firmware/seeeduino_v4_bootloader.hex'
TEST_PROGRAM = 'firmware/seeeduino_v4_test.hex'

class SeeeduinoV4():
    '''
    Seeeduino V4
    '''

    def __init__(self, device):
        self.device = device

    def write_interface(self):
        print('Write Seeeduino V4 interface firmware')

        cmd = AVRDUDE + ' -c avrispmkII -P usb -p m16u2 -U lfuse:w:0xEF:m -U hfuse:w:0xD9:m -U efuse:w:0xF4:m -U flash:w:' + INTERFACE
        self.device.select_spi(1)
        time.sleep(0.1)
        args = shlex.split(cmd)
        return subprocess.check_call(args)

    def write_bootloader(self):
        print('Write Seeeduino V4 booloader')

        cmd = AVRDUDE + ' -c avrispmkII -P usb -p m328p -U lfuse:w:0xFF:m -U hfuse:w:0xDA:m -U efuse:w:0x05:m -U flash:w:' + BOOTLOADER
        self.device.select_spi(0)
        time.sleep(0.01)
        args = shlex.split(cmd)
        return subprocess.check_call(args)

    def find_device(self):
        timeout = 10
        while timeout != 0:
            port = None
            for p in list_ports.comports():
                if p[2].upper().startswith('USB VID:PID=2886:0004'):
                    port = p[0]
                    return port

            sleep(1)
            timeout = timeout - 1

        print('No Seeeduino V4 is found')
        return None

    def write_test(self):
        print('Write Seeeduino V4 test program')

        port = self.find_device()
        if not port:
            return -1

        cmd = '%s -c avrispmkII -c arduino -P %s -b 115200 -p m328p -D -U flash:w:%s' % (AVRDUDE, port, TEST_PROGRAM)
        self.device.deselect_spi()
        time.sleep(0.01)
        args = shlex.split(cmd)
        return subprocess.check_call(args)

    def write_product(self):
       pass

    def test(self):

        last = self.device.read_io()
        # wait until io is stable
        while True:
            time.sleep(0.002)
            current = self.device.read_io()
            if current == last:
                break

            last = current

        first = last

        # wait until io is changed
        while True:
            current = self.device.read_io()
            if current != last:
                break

            last = current

        # wait until io is stable
        while True:
            time.sleep(0.002)
            current = self.device.read_io()
            if current == last:
                break

            last = current

        second = last


        print('IO: 0x%X -> 0x%X' % (first, second))

        self.device.enable_dc()
        voltage = []
        for i in range(8):
            voltage.append(self.device.read_voltage(i))

        print('Voltage: %s' % voltage)
        self.device.disable_dc()


        return (True, [first, second], voltage)

    def reset(self):
        pass
