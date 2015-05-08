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
    result = Signal(int, int)
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

    def setBoard(self, board):
        self.board = board

    def getBoard(self):
        return self.board

    def setBoardId(self, n):
        self.boardId = n

    def getBoardId(self):
        return self.boardId

    def setBoardState(self, n, state):
        self.result.emit(n, state)

class TPlanUI(QtGui.QMainWindow, Ui_MainWindow):
    def __init__(self, bridge):
        super(TPlanUI, self).__init__(None)
        self.setupUi(self)

        self.selectButton = self.selectButton1
        self.selectButton.setChecked(True)
        self.selectButtons = [self.selectButton1, self.selectButton2,
                              self.selectButton3, self.selectButton4]

        self.bridge = bridge

        self.bridge.setBoard(self.boardComboBox.currentText())
        self.bridge.setBoardId(1)
        self.bridge.output.connect(self.log)
        self.bridge.result.connect(self.on_result)
        self.bridge.disconnected.connect(self.on_disconnected)

        # self.selectButton1.setStyleSheet('QPushButton {background-color: rgb(255, 0, 0);}')

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
        self.clearButton.clicked.connect(self.logTextEdit.clear)

    def log(self, text):
        self.logTextEdit.append(text)

    def on_disconnected(self, reason):
        self.log(reason)
        if self.autoButton.text() == 'Stop':
            self.autoButton.setText('Auto Test')
            self.manualModeGroupBox.setEnabled(True)
            self.log('<<<< Stop auto test <<<<')

    def on_result(self, n, state):
        if state == 0:
            self.selectButtons[n].setStyleSheet('QPushButton {background-color: rgb(85, 98, 112);}')
        if state == 1:
            self.selectButtons[n].setStyleSheet('QPushButton {background-color: rgb(78, 205, 196);}')
        if state == 2:
            self.selectButtons[n].setStyleSheet('QPushButton {background-color: rgb(199, 244, 100);}')
        if state == 3:
            self.selectButtons[n].setStyleSheet('QPushButton {background-color: rgb(255, 107, 107);}')

    def on_board_changed(self, index):
        self.bridge.setBoard(self.boardComboBox.currentText())

    def on_auto_button_clicked(self):
        if self.autoButton.text() == 'Auto Test':
            self.bridge.put('start')

            self.manualGroupBox.setEnabled(False)
            self.autoButton.setText('Stop')
            self.log('>>>> Start auto test >>>>')
        else:
            self.bridge.put('stop')

            self.autoButton.setText('Auto Test')
            self.manualGroupBox.setEnabled(True)
            self.log('<<<< Stop auto test <<<<')

    def on_select_button_clicked(self):
        self.bridge.setBoardId(int(self.sender().text()))
        if self.selectButton is not self.sender():
            self.selectButton.setChecked(False)
        self.selectButton = self.sender()
        if not self.selectButton.isChecked():
            self.selectButton.setChecked(True)


    def on_bootloader_button_clicked(self):
        self.bridge.put('write bootloader')

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
