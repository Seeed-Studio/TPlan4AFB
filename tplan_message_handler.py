import threading
import time
import datetime
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
            self.bridge.log('\n============= search target =============')
            start_time = datetime.datetime.now()
            mask = 0
            for i in range(4):
                if self.dev.detect_target(i):
                    self.bridge.log('find target %d' % (i + 1))
                    mask |= 1 << i
                    self.bridge.setBoardState(i, 1)
                else:
                    self.bridge.setBoardState(i, 0)

            for i in range(4):
                if mask & (1 << i) == 0:
                    continue

                self.dev.select_target(i)

                time.sleep(0.1)
                # To do

                self.bridge.log('----------- test target %d -----------' % (i + 1))
                print('......... test target %d .........' % (i + 1))

                try:
                    has_error = False
                    while True:
                        if target.find_device():
                            self.bridge.log('skip writing interface firmware and bootloader')
                        else:
                            self.bridge.log('write interface firmware...')
                            if target.write_interface():
                                has_error = True
                                break
                            self.bridge.log('write bootloader...')
                            if target.write_bootloader():
                                has_error = True
                                break

                        self.bridge.log('write test program...')
                        if target.write_test():
                            has_error = True
                            break

                        self.bridge.log('ok')
                        time.sleep(2)
                        self.bridge.log('read test result...')
                        io_result, io_result_description, voltage_result, voltage_result_description = target.test()
                        if io_result:
                            self.bridge.log('IO test: ok')
                        else:
                            self.bridge.log('IO test: failed')
                            self.bridge.log(io_result_description)

                            has_error = True
                            break

                        if voltage_result:
                            self.bridge.log('Voltage test: ok')
                        else:
                            self.bridge.log('Voltage test: failed')
                            self.bridge.log(voltage_result_description)

                            has_error = True
                            break

                        # self.bridge.log('write product program...')
                        # target.write_product()

                        break

                    if has_error:
                        self.bridge.log('failed')
                        self.bridge.setBoardState(i, 3)
                    else:
                        self.bridge.log('......... test target %d done .........' % (i + 1))
                        self.bridge.setBoardState(i, 2)
                except subprocess.CalledProcessError as e:
                    self.bridge.log('failed')
                    self.bridge.log(e)
                    self.bridge.setBoardState(i, 3)

                self.dev.deselect_target(i)

            end_time = datetime.datetime.now()
            self.bridge.log('\ntime lapsed: %d' % (end_time - start_time).seconds)

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
                    time.sleep(3)
                    self.bridge.log('-------- %s --------' % message)
                    try:
                        has_error = False
                        if message == 'write interface':
                            if target.write_interface():
                                has_error = True
                        elif message == 'write bootloader':
                            if target.write_bootloader():
                                has_error = True
                        elif message == 'write program':
                            if target.write_test():
                                has_error = True
                        elif message == 'test target':
                            io_result, io_result_description, voltage_result, voltage_result_description = target.test()
                            if not io_result:
                                self.bridge.log('IO test: failed')
                                self.bridge.log(io_result_description)

                                has_error = True

                            if not voltage_result:
                                self.bridge.log('Voltage test: failed')
                                self.bridge.log(voltage_result_description)

                                has_error = True
                        elif message == 'write product':
                            target.write_product()

                        if has_error:
                            self.bridge.log('failed')
                        else:
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
