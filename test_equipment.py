"""

"""

from serial.tools import list_ports
from PyMata.pymata import PyMata, NoACK
import threading
import time

class TestEquipment():
    PWR_EN_PIN_GROUP = [49, 48, 47, 46]     # high to enable power
    DC_PWR_EN_PIN = 61                      # high to enable DC power
    SPI_EN_PIN_GROUP = [40, 41, 42, 43]     # low to select SPI
    TG_SPI_EN_PIN = 38                      # low to connect target with programmer
    IF_SPI_EN_PIN = 39                      # low to connect interface with programmer
    IF_RESET_PIN_GROUP = [53, 52, 51, 50]
    ID_PIN_GROUP = [28, 29, 44, 45]
    IO_PIN_GROUP = [14, 15, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 
                    30, 31, 32, 33, 34, 35, 36, 37, 22, 23, 24, 25, 26, 27]
    TG_DETECT_PIN = 69
    
    ADC_CONNECT_PIN_GROUP = [58, 59, 60]
    ADC_CHANNEL_PIN_GROUP = [54, 55, 56]
    
    ADC_I2C_SCL_PIN = 21
    ADC_I2C_SDA_PIN = 20
    ADC_I2C_ADDRESS = 0x52
    
    TG_NUMBER = 4
    
    def __init__(self, on_disconnected_cb=None):
        self.on_disconnected_cb = on_disconnected_cb
        self.firmata = None
        self.port = None
        self.target = 0
        self.target_detected_event = threading.Event()
        self.i2c_responsed_event = threading.Event()
        
        self.connected = False
        self.target_is_found = False
        
    def connect(self):
        if self.connected:
            return True
            
        for p in list_ports.comports():
            if p[2].upper().startswith('FTDIBUS\\VID_0403+PID_6001') or p[2].upper().startswith('USB VID:PID=0403:6001'):
                port = p[0]
                try:
                    firmata = PyMata(port, False, True, self.on_disconnected)
                    self.firmata = firmata
                    self.port = port
                    break
                except NoACK:
                    continue
                    
        if not self.port:
            return False
            
        self.config_io()
        
        self.connected = True
        return True
        
    def disconnect(self):
        if self.connected:
            self.firmata.close()
            
    def on_disconnected(self):
        self.disconneted = False
        self.firmata.close()
        self.on_disconnected_cb()
        
    def config_io(self):
        for pin in self.PWR_EN_PIN_GROUP + self.ADC_CONNECT_PIN_GROUP + self.ADC_CHANNEL_PIN_GROUP + [self.DC_PWR_EN_PIN]:
            self.firmata.set_pin_mode(pin, self.firmata.OUTPUT, self.firmata.DIGITAL)
            self.firmata.digital_write(pin, 0)
            
        for pin in self.SPI_EN_PIN_GROUP + self.IF_RESET_PIN_GROUP + [self.TG_SPI_EN_PIN, self.IF_SPI_EN_PIN]:
            self.firmata.set_pin_mode(pin, self.firmata.OUTPUT, self.firmata.DIGITAL)
            self.firmata.digital_write(pin, 1)
            
        for pin in self.ID_PIN_GROUP + self.IO_PIN_GROUP:
            self.firmata.set_pin_mode(pin, self.firmata.INPUT, self.firmata.DIGITAL)
            self.firmata.enable_digital_reporting(pin)
        
        self.firmata.set_pin_mode(self.TG_DETECT_PIN, self.firmata.INPUT, self.firmata.DIGITAL)
        self.firmata.set_digital_latch(self.TG_DETECT_PIN, 
                                       self.firmata.DIGITAL_LATCH_HIGH,
                                       self.on_target_detected)
        
        self.firmata.i2c_config(0, self.firmata.DIGITAL, self.ADC_I2C_SCL_PIN, self.ADC_I2C_SDA_PIN)
        self.firmata.i2c_write(self.ADC_I2C_ADDRESS, 0x02, 0x20)
        
        
    def enable_dc(self, enable=True):
        if enable:
            self.firmata.digital_write(self.DC_PWR_EN_PIN, 1)
        else:
            self.firmata.digital_write(self.DC_PWR_EN_PIN, 0)
            
    def disable_dc(self):
        self.firmata.digital_write(self.DC_PWR_EN_PIN, 0)
            
    def select_target(self, n):
        self.target = n
        for i in range(self.TG_NUMBER):
            if i != n:
                self.firmata.digital_write(self.PWR_EN_PIN_GROUP[i], 0)
        
        self.firmata.digital_write(self.PWR_EN_PIN_GROUP[n], 1)
            
    def deselect_target(self, n):
        self.firmata.digital_write(self.PWR_EN_PIN_GROUP[n], 0) 
            
    def select_spi(self, position):
        for i in range(self.TG_NUMBER):
            if i != self.target:
                self.firmata.digital_write(self.SPI_EN_PIN_GROUP[i], 1)
                
        self.firmata.digital_write(self.SPI_EN_PIN_GROUP[self.target], 0)    
                
        if position == 0:
            self.firmata.digital_write(self.IF_SPI_EN_PIN, 1)
            self.firmata.digital_write(self.TG_SPI_EN_PIN, 0)
        else:
            self.firmata.digital_write(self.TG_SPI_EN_PIN, 1)
            self.firmata.digital_write(self.IF_SPI_EN_PIN, 0)
            
    def deselect_spi(self):
        for i in range(self.TG_NUMBER):
            self.firmata.digital_write(self.SPI_EN_PIN_GROUP[i], 1)
            
        self.firmata.digital_write(self.IF_SPI_EN_PIN, 1)
        self.firmata.digital_write(self.TG_SPI_EN_PIN, 0)
        
    def read_io(self):
        bus = 0
        for i in range(len(self.IO_PIN_GROUP)):
            bus |= self.firmata.digital_read(self.IO_PIN_GROUP[i]) << i
            
        return bus
        
    def read_id(self):
        if not self.firmata.digital_read(self.TG_DETECT_PIN):
            return -1
        
        id = 0
        for i in range(len(self.ID_PIN_GROUP)):
            id |= self.firmata.digital_read(self.ID_PIN_GROUP[i]) << i
        
        return id
        
    def read_voltage(self, channel):
        self.firmata.digital_write(self.ADC_CONNECT_PIN_GROUP[0], self.target & 1)
        self.firmata.digital_write(self.ADC_CONNECT_PIN_GROUP[1], (self.target >> 1) & 1)
        self.firmata.digital_write(self.ADC_CONNECT_PIN_GROUP[2], 0)
        
        self.firmata.digital_write(self.ADC_CHANNEL_PIN_GROUP[0], channel & 1)
        self.firmata.digital_write(self.ADC_CHANNEL_PIN_GROUP[1], (channel >> 1) & 1)
        self.firmata.digital_write(self.ADC_CHANNEL_PIN_GROUP[2], (channel >> 2) & 1)
        
        time.sleep(0.1)
        
        return self.read_adc() * 6
       
    def read_adc(self):
        self.firmata.i2c_read(self.ADC_I2C_ADDRESS, 0x0, 2, self.firmata.I2C_READ, self.on_i2c_responsed)
        if not self.i2c_responsed_event.wait(3):
            print('read adc timeout')
            return 0
            
        self.i2c_responsed_event.clear()
        return self.voltage
        
    def detect_target(self, position):
        self.firmata.digital_write(self.ADC_CONNECT_PIN_GROUP[0], position & 1)
        self.firmata.digital_write(self.ADC_CONNECT_PIN_GROUP[1], (position >> 1) & 1)
        self.firmata.digital_write(self.ADC_CONNECT_PIN_GROUP[2], 1)
        
        time.sleep(0.1)
        
        if self.read_adc() > 3.0:
            return True
        
        return False
        
    def wait_for_target(self, timeout=None):
        print('wait for target')
        if self.target_is_found:
            self.target_detected_event.clear()
        if not self.target_detected_event.wait(timeout):
            self.target_is_found = False
            return False
            
        self.target_detected_event.clear()
        self.target_is_found = True
        return True
        
    def on_target_detected(self, data):
        print('target detected')
        self.target_detected_event.set()
        self.firmata.set_digital_latch(self.TG_DETECT_PIN, 
                                       self.firmata.DIGITAL_LATCH_HIGH,
                                       self.on_target_detected)
    
    def on_i2c_responsed(self, data):
        # print('i2c read: %s' % data)
        self.voltage = (((data[2][1] & 0xf) << 8) + data[2][2]) * 3.64 / 4096
        # print('voltage = %f' % self.voltage)
        self.i2c_responsed_event.set()
        
        
