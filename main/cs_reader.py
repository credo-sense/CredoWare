import datetime
import logging
from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import QTimer, QDateTime, QDate, QTime
from PyQt5.QtWidgets import *
from main_window import Ui_MainWindow
from sentry_sdk import capture_exception
from main import utils
from main.custom_dialog import CustomDialog
from main.data_reader import DataReader
from main.logger_data_plot import LoggerPlotWindow
from main.task_consumer import TaskConsumer, TaskTypes, Task
from main.utils import CONSCIOUS_BATTERY_LEVEL
import sentry_sdk

sentry_sdk.init("https://e6fdc5ed07fb4248aaf35c1deca4ec8b@sentry.io/2500238")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MainWindow(QMainWindow, Ui_MainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.btn_read_logger_data.pressed.connect(self.start_reading_logger_data)
        self.btn_set_logging_interval.pressed.connect(self.set_logging_interval)
        self.btn_device_rename.pressed.connect(self.rename_device)
        self.checkBox_dst.clicked.connect(self.toogle_dst)
        self.btn_sync_device_system_time.pressed.connect(self.sync_device_and_system_time)
        self.btn_set_alarm.pressed.connect(self.set_alarm)
        self.btn_erase_data.pressed.connect(self.erase_data)

        self.comboBox_logging_start.currentIndexChanged.connect(self.logging_start_selection_changed)
        self.comboBox_logging_stop.currentIndexChanged.connect(self.logging_stop_selection_changed)
        self.dateTimeEdit_logging_start.setDateTime(QDateTime.currentDateTime())
        self.dateTimeEdit_logging_stop.setDateTime(QDateTime.currentDateTime())
        self.dateTimeEdit_logging_start.hide()
        self.dateTimeEdit_logging_stop.hide()
        self.btn_set_start_stop_option.pressed.connect(self.set_logging_start_stop)

        self.show()

        self.queue_timer = QTimer()
        self.init_queue_task_consumer_thread()

        self.miscellaneous_timer = QTimer()
        self.init_miscellaneous_task_consumer_thread()

        self.device_connectivity_status_timer = QTimer()
        self.init_check_device_connectivity_status()

    def init_queue_task_consumer_thread(self):
        self.queue_timer.setInterval(500)
        self.queue_timer.timeout.connect(self.consume_queue_task)

    def init_miscellaneous_task_consumer_thread(self):
        self.miscellaneous_timer.setInterval(1000)
        self.miscellaneous_timer.timeout.connect(self.consume_miscellaneous_task)

    def init_check_device_connectivity_status(self):
        self.device_connectivity_status_timer.setInterval(1000)
        self.device_connectivity_status_timer.timeout.connect(self.check_device_connectivity_status)
        self.device_connectivity_status_timer.start()

    def consume_queue_task(self):
        TaskConsumer().consume_task()

    def consume_miscellaneous_task(self):
        self.update_system_time()
        self.update_device_time()

    def check_device_connectivity_status(self):
        dr = DataReader()
        device = dr.get_connected_device()

        if device:
            if not self.queue_timer.isActive():
                self.queue_timer.start()

            if not self.miscellaneous_timer.isActive():
                self.miscellaneous_timer.start()

            if not dr.is_port_open():
                self.label_device_id.setText('Reader found ! Connecting logger...')
                TaskConsumer().insert_task(Task(TaskTypes.SERIAL_OPEN, self.task_done_callback))

        else:
            self.after_device_not_found_change()

    def after_device_not_found_change(self):
        self.queue_timer.stop()
        self.miscellaneous_timer.stop()
        TaskConsumer().clear_task_queue()
        DataReader().close()

        self.label_device_id.setText('Reader not found !')
        self.label_device_type.setText("")
        self.label_battery_level.setText("")
        self.label_battery_level_low_signal.setText("")
        self.label_device_time.setText("")
        self.lineEdit_device_name.setText("")

    def rename_device(self):
        new_name = self.lineEdit_device_name.text()
        TaskConsumer().insert_task(Task(TaskTypes.SERIAL_RENAME_DEV_NAME, self.task_done_callback, new_name))

    def erase_data(self):
        reply = QtGui.QMessageBox.question(self, 'Message', "Are you sure ? All data will be deleted with this action.",
                                           QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.Yes:
            logger.debug("worked")
            TaskConsumer().insert_task(Task(TaskTypes.SERIAL_ERASE, self.task_done_callback))

    def set_logging_start_stop(self):
        start_status = self.comboBox_logging_start.currentIndex()
        stop_status = self.comboBox_logging_stop.currentIndex()
        cdt = QDateTime.currentDateTime()

        if start_status == 1 and self.dateTimeEdit_logging_start.dateTime() <= cdt:
            self.show_alert_dialog("Start: date & time can't be less than current date & time.")
            return

        if stop_status == 1 and self.dateTimeEdit_logging_stop.dateTime() <= cdt:
            self.show_alert_dialog("Stop: date & time can't be less than current date & time.")
            return

        if start_status == 1 and stop_status == 1:
            if self.dateTimeEdit_logging_start.dateTime() >= self.dateTimeEdit_logging_stop.dateTime():
                self.show_alert_dialog("Start date & time should be greater than stop date & time.")
                return

        start_td = self.dateTimeEdit_logging_start.dateTime().toString("hh:mm:ss d/M/yy")
        stop_td = self.dateTimeEdit_logging_stop.dateTime().toString("hh:mm:ss d/M/yy")
        w_str = " ".join([str(start_status), start_td, str(stop_status), stop_td])
        TaskConsumer().insert_task(Task(TaskTypes.SERIAL_WRITE_LOG_START_STOP, self.task_done_callback, w_str))

    def set_alarm(self):
        high_temp = int(self.lineEdit_high_temp.text())
        low_temp = int(self.lineEdit_low_temp.text())
        if low_temp > high_temp:
            self.show_alert_dialog("High temperature should be greater than low temperature.")
            return
        elif high_temp > 85:
            self.show_alert_dialog("High temperature can be maximum 85.")
            return
        elif low_temp < -45:
            self.show_alert_dialog("Low temperature should be greater than or equal to -45.")
            return

        if self.checkBox_temp_alarm_status.isChecked():
            new_str = " ".join(["1", str(high_temp), str(low_temp)])
        else:
            new_str = " ".join(["0", str(high_temp), str(low_temp)])

        TaskConsumer().insert_task(Task(TaskTypes.SERIAL_WRITE_ALARM, self.task_done_callback, new_str))

    def logging_start_selection_changed(self, i):
        if i == 0:
            self.dateTimeEdit_logging_start.hide()
        else:
            self.dateTimeEdit_logging_start.show()

    def logging_stop_selection_changed(self, i):
        if i == 0:
            self.dateTimeEdit_logging_stop.hide()
        else:
            self.dateTimeEdit_logging_stop.show()

    def toogle_dst(self):
        new_str = '1' if self.checkBox_dst.isChecked() else "0"
        TaskConsumer().insert_task(Task(TaskTypes.SERIAL_WRITE_DAYLIGHT, self.task_done_callback, new_str))

    def update_system_time(self):
        current_dt = datetime.datetime.now()
        self.label_system_time.setText(current_dt.strftime("%H:%M %d/%m/%Y"))

    def update_device_time(self):
        if utils.CURRENT_DEVICE_TIME_RESPONSE:
            utils.CURRENT_DEVICE_TIME_RESPONSE = utils.CURRENT_DEVICE_TIME_RESPONSE + datetime.timedelta(seconds=1)
            self.label_device_time.setText(utils.CURRENT_DEVICE_TIME_RESPONSE.strftime("%H:%M %d/%m/%Y"))

    def sync_device_and_system_time(self):
        dt_str = datetime.datetime.now().strftime('%H:%M:%S %d/%m/%y')
        TaskConsumer().insert_task(Task(TaskTypes.SERIAL_WRITE_TIME, self.task_done_callback, dt_str))

    def task_done_callback(self, response):
        print(f"task response : {response}")

        if 'exception' in response:
            return

        if response['task_type'] == TaskTypes.SERIAL_OPEN:
            TaskConsumer().insert_task(Task(TaskTypes.SERIAL_READING_MODE, self.task_done_callback))

        elif response['task_type'] == TaskTypes.SERIAL_READING_MODE:
            data = response['data']

            if data == 'no_device':
                self.label_device_id.setText('No reader found !')
                TaskConsumer().insert_task(Task(TaskTypes.SERIAL_READING_MODE, self.task_done_callback))

            elif data == 'not_found':
                self.label_device_id.setText('Reader found but not in reading mode !')
                TaskConsumer().insert_task(Task(TaskTypes.SERIAL_READING_MODE, self.task_done_callback))

            elif data == 'found':
                TaskConsumer().insert_task(Task(TaskTypes.SERIAL_DEV_ID, self.task_done_callback))
                TaskConsumer().insert_task(Task(TaskTypes.SERIAL_DEV_NAME, self.task_done_callback))
                TaskConsumer().insert_task(Task(TaskTypes.SERIAL_READ_LOG, self.task_done_callback))
                TaskConsumer().insert_task(Task(TaskTypes.SERIAL_READ_CONST, self.task_done_callback))
                TaskConsumer().insert_task(Task(TaskTypes.SERIAL_TIME_BATTERY, self.task_done_callback))
                TaskConsumer().insert_task(Task(TaskTypes.SERIAL_READ_DAYLIGHT, self.task_done_callback))
                TaskConsumer().insert_task(Task(TaskTypes.SERIAL_READ_ALARM, self.task_done_callback))

        elif response['task_type'] == TaskTypes.SERIAL_DEV_ID:
            self.label_device_id.setText(response['data'])
            lst = response['data'].split('-')
            if lst[1] == 'T':
                self.label_device_type.setText('Temperature Logger')

        elif response['task_type'] == TaskTypes.SERIAL_TIME_BATTERY:
            time, date, battery = response['data'].strip().split()
            self.label_battery_level.setText(battery + " V")
            if float(battery.strip()) <= CONSCIOUS_BATTERY_LEVEL:
                self.label_battery_level_low_signal.setText("Please change your battery.")

            datetime_str = date + ' ' + time
            datetime_object = datetime.datetime.strptime(datetime_str, '%d/%m/%Y %H:%M:%S')
            utils.CURRENT_DEVICE_TIME_RESPONSE = datetime_object
            self.update_device_time()

        elif response['task_type'] == TaskTypes.SERIAL_DEV_NAME:
            self.lineEdit_device_name.setText(response['data'])

        elif response['task_type'] == TaskTypes.SERIAL_READ_CONST:
            utils.READ_CONST_RESPONSE = response['data']
            # print(utils.READ_CONST_RESPONSE)

        elif response['task_type'] == TaskTypes.SERIAL_READ_LOGGER_DATA:
            self.msg_box_read_log_data.close()
            logger_plot_window = LoggerPlotWindow(self)
            logger_plot_window.initialize_and_show(self.interval, response['data'])

        elif response['task_type'] == TaskTypes.SERIAL_RENAME_DEV_NAME:
            self.show_alert_dialog("Device rename successful!")

        elif response['task_type'] == TaskTypes.SERIAL_WRITE_TIME:
            TaskConsumer().insert_task(Task(TaskTypes.SERIAL_TIME_BATTERY, self.task_done_callback))
            self.show_alert_dialog("Write time successful!")

        elif response['task_type'] == TaskTypes.SERIAL_WRITE_LOG:
            self.show_alert_dialog("Logging interval set successful!")

        elif response['task_type'] == TaskTypes.SERIAL_ERASE:
            self.show_alert_dialog("All data deleted.")

        elif response['task_type'] == TaskTypes.SERIAL_WRITE_LOG_START_STOP:
            self.show_alert_dialog("Logging start stop time setting successful!")

        elif response['task_type'] == TaskTypes.SERIAL_READ_ALARM:
            alarm_status, high_temp_value, low_temp_value = response['data'].split()

            if alarm_status == '1':
                self.checkBox_temp_alarm_status.setChecked(True)
                self.lineEdit_high_temp.setText(high_temp_value)
                self.lineEdit_low_temp.setText(low_temp_value)
            else:
                self.checkBox_temp_alarm_status.setChecked(False)
                self.lineEdit_high_temp.setText(high_temp_value)
                self.lineEdit_low_temp.setText(low_temp_value)

        elif response['task_type'] == TaskTypes.SERIAL_WRITE_ALARM:
            self.show_alert_dialog("Write alarm successful!")

        elif response['task_type'] == TaskTypes.SERIAL_READ_LOG:
            utils.READ_LOG_RESPONSE = response['data']
            self.interval, start_type, start_time, start_date, stop_type, stop_time, stop_date = response['data'].split()
            self.lineEdit_logging_interval.setText(self.interval)
            self.update_logging_start_stop(start_type, start_time, start_date, stop_type, stop_time, stop_date)

        elif response['task_type'] == TaskTypes.SERIAL_WRITE_DAYLIGHT:
            if self.checkBox_dst.isChecked():
                self.show_alert_dialog("Daylight saving turned on successfully!")
            else:
                self.show_alert_dialog("Daylight saving turned off successfully!")

        elif response['task_type'] == TaskTypes.SERIAL_READ_DAYLIGHT:
            if response['data'] == '1':
                self.checkBox_dst.setChecked(True)
            else:
                self.checkBox_dst.setChecked(False)

    def update_logging_start_stop(self, start_type, start_time, start_date, stop_type, stop_time, stop_date):

        if start_type == '0':
            self.comboBox_logging_start.setCurrentIndex(0)
        else:
            self.comboBox_logging_start.setCurrentIndex(1)
            hour, minutes, seconds = start_time.split(':')
            dtf = datetime.datetime.strptime(start_date, '%d/%m/%y')
            dt = QtCore.QDateTime(QDate(dtf.year, dtf.month, dtf.day), QTime(int(hour), int(minutes), int(seconds)))
            self.dateTimeEdit_logging_start.setDateTime(dt)

        if stop_type == '0':
            self.comboBox_logging_stop.setCurrentIndex(0)
        else:
            self.comboBox_logging_stop.setCurrentIndex(1)
            hour, minutes, seconds = stop_time.split(':')
            dtf = datetime.datetime.strptime(stop_date, '%d/%m/%y')
            dt = QtCore.QDateTime(QDate(dtf.year, dtf.month, dtf.day), QTime(int(hour), int(minutes), int(seconds)))
            self.dateTimeEdit_logging_stop.setDateTime(dt)

    def set_logging_interval(self):
        interval_value = self.lineEdit_logging_interval.text()

        if interval_value == "":
            self.show_alert_dialog("Interval can't be empty.")
            return

        elif not interval_value.isnumeric() or int(interval_value) > 1440:
            self.show_alert_dialog("Interval value should be positive and numeric(range 0 to 1440).")
            return

        TaskConsumer().insert_task(Task(TaskTypes.SERIAL_WRITE_LOG, self.task_done_callback, interval_value))

    def start_reading_logger_data(self):
        TaskConsumer().insert_task(Task(TaskTypes.SERIAL_READ_LOGGER_DATA, self.task_done_callback))
        self.msg_box_read_log_data = CustomDialog(self)
        self.msg_box_read_log_data.show()

    def show_alert_dialog(self, msg):
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setText(msg)
        msg_box.setWindowTitle("Message")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Message', "Are you sure to quit?", QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.queue_timer.stop()
            self.miscellaneous_timer.stop()
            self.device_connectivity_status_timer.stop()
            TaskConsumer().clear_task_queue()
            DataReader().close()
            event.accept()
        else:
            event.ignore()


if __name__ == '__main__':
    try:
        app = QApplication([])
        app.setApplicationName("CS Reader")
        app.setWindowIcon(QtGui.QIcon("../icon.png"))
        window = MainWindow()
        window.setFixedSize(684, 866)
        app.exec_()
    except Exception as e:
        capture_exception(e)
    finally:
        pass


