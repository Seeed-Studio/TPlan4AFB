"""

"""

from serial.tools import list_ports
from PyMata.pymata import PyMata, NoACK

class TestEquipment():
    PWR_EN_PIN_GROUP = [49, 48, 47, 46]     # high to enable power
    DC_PWR_EN_PIN = 61                      # high to enable DC power
    SPI_EN_PIN_GROUP = [40, 41, 42, 43]     # low to select SPI
    TG_SPI_EN_PIN = 38                      # low to connect target with programmer
    IF_SPI_EN_PIN = 39                      # low to connect interface with programmer
    IF_RESET_PIN_GROUP = [53, 52, 51, 50]
    ID_PIN_GROUP = [28, 29, 44, 45]
    IO_PIN_GROUP = [14, 15, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 30, 31, 32, 33, 34, 35, 36, 37, 22, 23, 24, 25, 26, 27]
    ACTION_DETECT_PIN = 1
    
    TG_NUMBER = 4
    
    def __init__(self, reporter=None):
        self.reporter = reporter
        self.firmata = None
        self.port = None
        self.target = 0
        
    def connect(self):
        for p in list_ports.comports():
            if p[2].upper().startswith('FTDIBUS\\VID_0403+PID_6001'):
                port = p[0]
                try:
                    firmata = PyMata(port, False, True, self.reporter)
                    self.firmata = firmata
                    self.port = port
                    break
                except NoACK:
                    continue
                    
        if not self.port:
            return False
            
        self.config_io()
        return True
        
    def disconnect(self):
        if self.firmata:
            self.firmata.close()
        
    def config_io(self):
        for pin in self.PWR_EN_PIN_GROUP + [self.DC_PWR_EN_PIN]:
            self.firmata.set_pin_mode(pin, self.firmata.OUTPUT, self.firmata.DIGITAL)
            self.firmata.digital_write(pin, 0)
            
        for pin in self.SPI_EN_PIN_GROUP + self.IF_RESET_PIN_GROUP + [self.TG_SPI_EN_PIN, self.IF_SPI_EN_PIN]:
            self.firmata.set_pin_mode(pin, self.firmata.OUTPUT, self.firmata.DIGITAL)
            self.firmata.digital_write(pin, 1)
            
        for pin in self.ID_PIN_GROUP + self.IO_PIN_GROUP:
            self.firmata.set_pin_mode(pin, self.firmata.INPUT, self.firmata.DIGITAL)
            self.firmata.enable_digital_reporting(pin)
            
    def select_target(self, n):
        self.target = n
        for i in range(self.TG_NUMBER):
            if i != n:
                self.firmata.digital_write(self.PWR_EN_PIN_GROUP[i], 0)
            
            self.firmata.digital_write(self.PWR_EN_PIN_GROUP[n], 1)
                
    def select_spi(self, spi):
        for i in range(self.TG_NUMBER):
            if i != self.target:
                self.firmata.digital_write(self.SPI_EN_PIN_GROUP[i], 1)
                
            self.firmata.digital_write(self.SPI_EN_PIN_GROUP[self.target], 0)    
                
        if spi == 0:
            self.firmata.digital_write(self.IF_SPI_EN_PIN, 1)
            self.firmata.digital_write(self.TG_SPI_EN_PIN, 0)
        else:
            self.firmata.digital_write(self.TG_SPI_EN_PIN, 1)
            self.firmata.digital_write(self.IF_SPI_EN_PIN, 0)
            
    def deselect_spi(self):
        for i in range(self.TG_NUMBER):
            self.firmata.digital_write(self.SPI_EN_PIN_GROUP[i], 1)
            
        self.firmata.digital_write(self.IF_SPI_EN_PIN, 1)
        self.firmata.digital_write(self.TG_SPI_EN_PIN, 1)
        
    def read_io(self):
        bus = 0
        for i in range(len(self.IO_PIN_GROUP)):
            bus |= self.firmata.digital_read(self.IO_PIN_GROUP[i]) << i
            
        return bus
        
    def read_id(self):
        id = 0
        for i in range(len(self.ID_PIN_GROUP)):
            id |= self.firmata.digital_read(self.ID_PIN_GROUP[i]) << i
        
        return id
