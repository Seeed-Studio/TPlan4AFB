

import threading
import time
from test_equipment import TestEquipment
from target import TARGET
import subprocess

class TPlanMessageHandler():
    """
     This class handle messages from UI
    """

    def __init__(self, bridge):

        self.bridge = bridge
        self.stop_event = threading.Event()
        self.dev = TestEquipment(self.on_dev_disconnected)

        self.exit_auto = threading.Event()

        self.message_thread = threading.Thread(target=self.handle_message)

    def run_auto_test(self):

        while not self.exit_auto.is_set():
            if not self.dev.wait_for_target(2):
                continue

            board = self.bridge.getBoard()
            target = TARGET[board](self.dev)
            self.bridge.log('----------- search target -----------')
            start_time = time.time()
            self.dev.enable_dc()
            mask = 0
            for i in range(4):
                if self.dev.detect_target(i):
                    self.bridge.log('find target %d' % (i + 1))
                    mask |= 1 << i
                    self.bridge.setBoardState(i, 1)
                else:
                    self.bridge.setBoardState(i, 0)

            self.dev.enable_dc(False)

            for i in range(4):
                if mask & (1 << i) == 0:
                    continue

                self.dev.select_target(i)

                time.sleep(0.1)
                # To do

                self.bridge.log('>> test target %d' % (i + 1))
                print('************** test target %d ***************' % (i + 1))

                try:
                    self.bridge.log('1. write interface firmware...')
                    target.write_interface()
                    self.bridge.log('ok')
                    self.bridge.log('2. write bootloader...')
                    target.write_bootloader()
                    self.bridge.log('ok')

                    self.bridge.log('3. write test program...')
                    if target.write_test():
                        self.dev.deselect_target(i)
                        self.bridge.log('failed')
                        self.bridge.setBoardState(i, 3)
                        continue

                    self.bridge.log('ok')
                    time.sleep(2)
                    self.bridge.log('4. read test result...')
                    result, io, voltage = target.test()
                    self.bridge.log('IO: 0x%X - 0x%X' % (io[0], io[1]))
                    self.bridge.log('Voltage: %s' % voltage)

                    self.bridge.log('5. write product program...')
                    target.write_product()
                    self.dev.deselect_target(i)

                    self.bridge.log('<< test target %d done' % (i + 1))

                    self.dev.deselect_target(i)
                    self.bridge.setBoardState(i, 2)
                except subprocess.CalledProcessError as e:
                    self.bridge.log('failed')
                    self.bridge.log(e)
                    self.bridge.setBoardState(i, 3)
                    continue

            end_time = time.time()
            self.bridge.log('time lapsed: %d' % (end_time - start_time))

    def handle_message(self):
        while True:
            message = self.bridge.get()
            print(message)
            if message == 'start':
                if self.dev.connect():
                    self.auto_test_thread = threading.Thread(target=self.run_auto_test)
                    self.exit_auto.clear()
                    self.auto_test_thread.start()
            elif message == 'stop':
                self.exit_auto.set()
            elif message == 'quit':
                self.exit_auto.set()
                self.stop_event.set()
                break
            else:
                if self.dev.connect():
                    board = self.bridge.getBoard()
                    target = TARGET[board](self.dev)
                    index = self.bridge.getBoardId() - 1
                    self.dev.select_target(index)
                    self.bridge.log('-------- %s --------' % message)
                    try:
                        if message == 'write interface':
                            target.write_interface()
                        elif message == 'write bootloader':
                            target.write_bootloader()
                        elif message == 'write program':
                            target.write_test()

                        self.bridge.log('ok')
                    except subprocess.CalledProcessError as e:
                        self.bridge.log('failed')
                        self.bridge.log(e)

                    # self.dev.deselect_target(index)

    def start(self):
        self.message_thread.start()

    def join(self):
        self.exit_auto.set()
        self.stop_event.set()
        self.dev.disconnect()
        self.message_thread.join()

    def on_dev_disconnected(self):
        self.exit_auto.set()
        self.bridge.disconnect('device is disconnected')
