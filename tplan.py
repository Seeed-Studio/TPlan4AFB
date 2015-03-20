#!/usr/bin/python
 
# -*- coding: utf-8 -*-
 
import sys
import os
from PySide.QtGui import *
from PySide.QtCore import *
from tplan_ui import *
from tplan_message_handler import TPlanMessageHandler
import Queue

app_path = os.path.dirname(os.path.realpath(sys.argv[0]))

class Bridge(QObject):
    output = Signal(str)
    disconnected = Signal(str)
    
    def __init__(self):
        QObject.__init__(self)
        self.queue = Queue.Queue()
        
    def log(self, message):
        self.output.emit(message)
        
    def disconnect(self, reason):
        self.disconnected.emit(reason)
        
    def put(self, message):
        self.queue.put(message)
        
    def get(self):
        return self.queue.get()
        
    def empty(self):
        return self.queue.empty()
 
class TPlanUI(QtGui.QMainWindow, Ui_MainWindow):
    def __init__(self, bridge):
        super(TPlanUI, self).__init__(None)
        self.setupUi(self)
        
        self.selectButton = self.selectButton1
        self.selectButton.setChecked(True)
        
        self.bridge = bridge
        
        self.bridge.output.connect(self.log)
        self.bridge.disconnected.connect(self.on_disconnected)
        
        self.autoButton.clicked.connect(self.on_auto_button_clicked)
        self.selectButton1.clicked.connect(self.on_select_button_clicked)
        self.selectButton2.clicked.connect(self.on_select_button_clicked)
        self.selectButton3.clicked.connect(self.on_select_button_clicked)
        self.selectButton4.clicked.connect(self.on_select_button_clicked)
        self.bootloaderButton.clicked.connect(self.on_bootloader_button_clicked);
        self.programButton.clicked.connect(self.on_program_button_clicked)
        self.interfaceButton.clicked.connect(self.on_interface_button_clicked)
        self.testButton.clicked.connect(self.on_test_button_clicked)
        self.resetButton.clicked.connect(self.on_reset_button_clicked)

    def log(self, text):
        self.logTextEdit.append(text)
        
    def on_disconnected(self, reason):
        self.log(reason)
        if self.autoButton.text() == 'Stop':
            self.autoButton.setText('Start')
            self.manualModeGroupBox.setEnabled(True)
            self.log('<<<<Stop auto test mode<<<<')
                
    def on_auto_button_clicked(self):
        if self.autoButton.text() == 'Start':
            self.bridge.put('start')
            
            self.manualModeGroupBox.setEnabled(False)
            self.autoButton.setText('Stop')
            self.log('>>>>Start auto test mode>>>>')
        else:
            self.bridge.put('stop')
            
            self.autoButton.setText('Start')
            self.manualModeGroupBox.setEnabled(True)
            self.log('<<<<Stop auto test mode<<<<')
        
    def on_select_button_clicked(self):
        self.bridge.put('select ' + self.sender().text())
        if self.selectButton is not self.sender():
            self.selectButton.setChecked(False)
        self.selectButton = self.sender()
        if not self.selectButton.isChecked():
            self.selectButton.setChecked(True)
            
        
    def on_bootloader_button_clicked(self):
        self.bridge.put('write booloader')
        
    def on_program_button_clicked(self):
        self.bridge.put('write program')
        
    def on_interface_button_clicked(self):
        self.bridge.put('write interface')
        
    def on_test_button_clicked(self):
        self.bridge.put('test target')
        
    def on_reset_button_clicked(self):
        self.bridge.put('reset target')
        
    def closeEvent(self, event):
        self.bridge.put('quit')
        # close all threads
        event.accept()
 
if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    bridge = Bridge()
    message_handler = TPlanMessageHandler(bridge)
    message_handler.start()
    window = TPlanUI(bridge)
    
    window.show()
    app.exec_()
    message_handler.join()
    sys.exit(0)