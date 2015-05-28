'''
+ write interface
avrdude -c avrispmkII -P usb -p m16u2 -U lfuse:w:0xEF:m -U hfuse:w:0xD9:m -U efuse:w:0xF4:m -U flash:w:interface.hex

+ write booloader
avrdude -c avrispmkII -P usb -p m328p -U lfuse:w:0xFF:m -U hfuse:w:0xDE:m -U efuse:w:0x05:m -U flash:w:bootloader.hex

+ write program
avrdude -c arduino -P {COMx} -b 115200 -p m328p -D -U flash:w:program.hex
'''

import subprocess
import datetime
import shlex
from serial.tools import list_ports
from time import sleep

MAX_VOLTAGE = [5.25, 3.47, 5.25, 5.25, 5.25, 5.25, 5.25, 5.25]
MIN_VOLTAGE = [4.75, 3.14, 4.75, 0.0, 0.0, 0.0, 0.0, 4.75]
PIN_NAME = ['D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7',
            'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'D14/SDA', 'D15/SCL',
            'A0', 'A1', 'A2', 'A3', 'A4', 'A5',
             'G1_1', 'G1_2', 'G2_1', 'G2_2', 'G3_1', 'G3_2',
            'SCK/D13', 'MISO/D12', 'MOSI/D11', 'IF_MOSI', 'IF_MISO', 'IF_SCK']
PIN_MASK = 0x1FFFFFFF

AVRDUDE = 'external/avrdude'

INTERFACE  = 'firmware/seeeduino_v4_interface.hex'
BOOTLOADER = 'firmware/seeeduino_v4_bootloader.hex'
TEST_PROGRAM = 'firmware/seeeduino_v4_test.hex'

def timeout_command(command, timeout = 10):
    """
    call shell-command and either return its output or kill it
    if it doesn't normally exit within timeout seconds and return None
    """

    if type(command) == type(''):
        command = shlex.split(command)
    start = datetime.datetime.now()
    process = subprocess.Popen(command) # , stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    resultcode = process.poll()
    while resultcode is None:
        now = datetime.datetime.now()
        if (now - start).seconds > timeout:
            process.kill()
            return -1
        sleep(0.01)
        resultcode = process.poll()
    return resultcode

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
        sleep(0.01)
        return timeout_command(cmd)

    def write_bootloader(self):
        print('Write Seeeduino V4 booloader')

        cmd = AVRDUDE + ' -c avrispmkII -P usb -p m328p -U lfuse:w:0xFF:m -U hfuse:w:0xDA:m -U efuse:w:0x05:m -U flash:w:' + BOOTLOADER
        self.device.select_spi(0)
        sleep(0.01)
        return timeout_command(cmd)

    def find_device(self):
        timeout = 10
        while timeout != 0:
            port = None
            for p in list_ports.comports():
                if p[2].upper().startswith('USB VID:PID=2886:0004'):
                    port = p[0]
                    print('find port: ' + port)
                    return port

            sleep(0.1)
            timeout = timeout - 1

        print('No Seeeduino V4 is found')
        return None

    def write_test(self):
        print('Write Seeeduino V4 test program')
        self.device.deselect_spi()
        sleep(1)
        port = self.find_device()
        if not port:
            return -1

        cmd = '%s -c avrispmkII -c arduino -P %s -b 115200 -p m328p -D -U flash:w:%s' % (AVRDUDE, port, TEST_PROGRAM)
        return timeout_command(cmd)

    def write_product(self):
       pass

    def test(self, timeout=1):
        starttime = datetime.datetime.now()
        startbit = self.device.read_io() & 1
        while startbit == (self.device.read_io() & 1):
            now = datetime.datetime.now()
            if (now - starttime).seconds > timeout:
                print('wait for io changes, timeout')
                break

        sleep(0.05)
        first = self.device.read_io()

        starttime = datetime.datetime.now()
        startbit = self.device.read_io() & 1
        while startbit == (self.device.read_io() & 1):
            now = datetime.datetime.now()
            if (now - starttime).seconds > timeout:
                print('wait for io changes, timeout')
                break
        sleep(0.05)
        second = self.device.read_io()

        print('IO: 0x%X -> 0x%X' % (first, second))

        io_error_bitmap = (~(first ^ second)) & PIN_MASK
        io_result_description = ''
        io_result = True
        if io_error_bitmap != 0:
            pin = 0
            while io_error_bitmap != 0:
                if io_error_bitmap & 1:
                    mask = 1 << pin
                    startbit = self.device.read_io() & mask
                    starttime = datetime.datetime.now()
                    while startbit == (self.device.read_io() & mask):
                        now = datetime.datetime.now()
                        if (now - starttime).seconds > timeout:
                            io_result = False
                            io_result_description += '[ %s is always %d ]' % (PIN_NAME[pin], startbit >> pin)
                            break
                pin += 1
                io_error_bitmap >>= 1

        print(io_result_description)

        self.device.enable_dc()
        self.device.read_voltage(0)  # First read may have error
        voltage_result = True
        voltage_result_description = ''
        voltage = []
        for i in range(8):
            v = self.device.read_voltage(i)
            if v < MIN_VOLTAGE[i] or v > MAX_VOLTAGE[i]:
                voltage_result = False
                voltage_result_description += '[ channel %d voltage %f is out of range %f - %f ]' % (i, v, MIN_VOLTAGE[i], MAX_VOLTAGE[i])
            voltage.append(v)

        self.device.disable_dc()
        print('Voltage: %s' % voltage)
        print(voltage_result_description)

        return (io_result, io_result_description, voltage_result, voltage_result_description)

    def reset(self):
        pass
