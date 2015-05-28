'''
Wrapper of Seeeduino Mega
'''

from serial.tools import list_ports
import serial
import threading
import time
import datetime


class Assistant():
    def __init__(self, on_disconnected=None):
        self.on_disconnected = on_disconnected
        self.serial = None
        self.serial_thread = None
        self.serial_received_line = None
        self.stop_event = threading.Event()
        self.target_detected_event = threading.Event()
        self.ack_event = threading.Event()
        self.line_received_event = threading.Event()
        self.is_connected = False
        self.target_mask = 0x00

    def connect(self):
        if self.is_connected:
            print('already connected')
            return True

        for p in list_ports.comports():
            if p[2].upper().startswith('FTDIBUS\\VID_0403+PID_6001') or p[2].upper().startswith(
                    'USB VID:PID=0403:6001'):
                print('find Seeeduino Mega')
                port = p[0]

                self.serial = serial.Serial(port=port,
                                            baudrate=115200,
                                            bytesize=8,
                                            stopbits=1,
                                            timeout=1)
        if not self.serial:
            return False

        self.serial_thread = threading.Thread(target=self.receive)
        self.serial_thread.start()

        time.sleep(1)
        print(datetime.datetime.now())
        self.send('init', 20)
        print(datetime.datetime.now())

        self.is_connected = True
        return True

    def disconnect(self):
        if self.is_connected:
            self.stop_event.set()
            self.serial_thread.join()
            self.serial.close()

    def send(self, message, timeout=1):
        try:
            print('tx:' + message)
            self.ack_event.clear()
            self.serial.write(message + '\r\n')
        except IOError as e:
            print(e)
            self.serial.close()
            self.stop_event.set()

            if self.on_disconnected:
                self.on_disconnected()

        if not self.ack_event.wait(timeout):
            print('wait for ok, timeout')
            return False

        return True

    def require(self, message, timeout=1):
        try:
            print('tx:' + message)
            self.line_received_event.clear()
            self.serial.write(message + '\r\n')
        except IOError as e:
            print(e)
            self.serial.close()
            self.stop_event.set()

            if self.on_disconnected:
                self.on_disconnected()

        if not self.line_received_event.wait(timeout):
            print('no response')
            return None

        return self.serial_received_line

    def receive(self):
        while not self.stop_event.is_set():
            try:
                line = self.serial.readline()
                if line:
                    print('rx:' + line)
                if line.startswith('start'):
                    self.target_mask = int(line.split()[1])
                    self.target_detected_event.set()
                elif line.startswith('ok'):
                    self.ack_event.set()
                else:
                    self.serial_received_line = line
                    self.line_received_event.set()

            except IOError as e:
                print(e)
                self.serial.close()
                self.stop_event.set()

                if self.on_disconnected:
                    self.on_disconnected()

    def wait_for_target(self, timeout=None):
        print('wait for target')
        self.target_detected_event.clear()
        if not self.target_detected_event.wait(timeout):
            return 0

        self.target_detected_event.clear()
        return self.target_mask

    def read_voltage(self):
        response = self.require('testvol')
        voltage = []
        for v in response.split():
            voltage.append(float(v))
        return voltage

    def read_io(self):
        response = self.require('testio')
        value = []
        for i in response.split():
            value.append(int(i))
        return value

    def select_spi(self, position):
        spi_select_commands = ['ifspi', 'mcuspi']
        self.send(spi_select_commands[position])

    def deselect_spi(self):
        self.send('program')

    def enable_dc(self):
        self.send('dcon')

    def disable_dc(self):
        self.send('dcoff')

    def select_target(self, n):
        usb_power_on_commands = ['pwra', 'pwrb', 'pwrc', 'pwrd']
        self.send(usb_power_on_commands[n])

    def power_off_targets(self, n):
        self.send('pwroff')
