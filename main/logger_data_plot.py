import collections
import datetime
import logging
import math
import os
import fpdf
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QFileDialog
from main import utils
from main.graph_window import Ui_ReadLoggerDataWindow
import matplotlib.dates as mdates
from matplotlib.backends.backend_qt5agg import (NavigationToolbar2QT as NavigationToolbar)


logger = logging.getLogger(__name__)


class LoggerPlotWindow(QMainWindow, Ui_ReadLoggerDataWindow):

    def __init__(self, *args, **kwargs):
        super(LoggerPlotWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.addToolBar(NavigationToolbar(self.MplWidget.canvas, self))
        self.comboBox_temp_unit.currentIndexChanged.connect(self.onCurrentIndexChanged)
        self.setWindowTitle("Graph Window")
        self.btn_generate_report.clicked.connect(self.generate_report)

    def initialize_and_show(self, interval, data):
        self.start_dt = ''
        self.end_dt = ''
        self.interval = int(interval)
        self.data = data
        self.populate_graph()
        self.show()

    def generate_report(self):
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setText("Choose format to generate report.")
        msg_box.setWindowTitle("Message")
        pdftBtn = msg_box.addButton('Pdf', QMessageBox.YesRole)
        csvBtn = msg_box.addButton('Csv', QMessageBox.NoRole)
        msg_box.exec_()
        if msg_box.clickedButton() == pdftBtn:
            print("pdf")
            self.choose_directory('pdf')
        elif msg_box.clickedButton() == csvBtn:
            print("csv")
            self.choose_directory('csv')

    def choose_directory(self, file_ext):
        qfd = QFileDialog(self)
        options = qfd.Options()
        options |= qfd.DontUseNativeDialog
        file_dir = qfd.getExistingDirectory(self, "Choose a folder", "", qfd.ShowDirsOnly)
        if file_dir:
            print(file_dir)
            self.write_data_to_file(file_ext, file_dir)

    def write_data_to_file(self, file_ext, file_dir):

        file_name_dt = []
        start_rt = self.start_dt.replace('/', '-')
        start_rt = start_rt.replace(':', '-')
        end_rt = self.end_dt.replace('/', '-')
        end_rt = end_rt.replace(':', '-')
        file_name_dt.extend(start_rt.split(" "))
        file_name_dt.extend(end_rt.split(" "))
        file_name = '_'.join(file_name_dt)
        combo_index = self.comboBox_temp_unit.currentIndex()
        if combo_index == 0:
            file_name = file_name + "_kelvin" + "." + file_ext
        else:
            file_name = file_name + "_celsius" + "." + file_ext
        full_file_path = os.path.join(file_dir, file_name)

        if file_ext == 'pdf':
            data_lst = []
            i = 0
            for x, y in zip(self.x_data, self.y_data):
                i += 1
                data_lst.append(str(i)+". " + str(x) + " : " + str(y) + "\n")

            pdf = fpdf.FPDF(format='letter')
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            for i in data_lst:
                pdf.write(5, str(i))
                pdf.ln()
            pdf.output(full_file_path)

        elif file_ext == 'csv':
            import csv
            with open(full_file_path, 'w+', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["index", "Log time", "Temperature"])
                i = 0
                for x, y in zip(self.x_data, self.y_data):
                    i += 1
                    writer.writerow([i, x, y])

    def onCurrentIndexChanged(self, ix):
        self.MplWidget.canvas.axes.cla()
        self.populate_graph()
        self.MplWidget.canvas.draw()

    def populate_graph(self):
        def_d = collections.defaultdict(list)
        for index, value in enumerate(self.data):
            if ' ' in value:
                t, d, n = value.split(' ')
                current_key = f"{t} {d}"
                if not self.start_dt:
                    self.start_dt = current_key
                else:
                    self.end_dt = current_key
            else:
                def_d[current_key].append(int(value))

        self.graph_start_dt.setText(f"Start : {self.start_dt}")
        self.graph_end_dt.setText(f"End : {self.end_dt}")

        self.x_data = []
        self.y_data = []
        for key, values in def_d.items():
            self.y_data.extend(self.apply_rules_to_values(values))
            dtf = datetime.datetime.strptime(key, "%H:%M:%S %d/%m/%Y")
            self.x_data.append(dtf)
            for index, value in enumerate(values):
                if index == 0:
                    continue
                dtf = dtf+datetime.timedelta(minutes=self.interval)
                self.x_data.append(dtf)
        logger.info(self.x_data)
        self.MplWidget.canvas.axes.plot_date(self.x_data, self.y_data, linestyle='solid')
        self.MplWidget.canvas.axes.xaxis.set_major_locator(mdates.AutoDateLocator())
        self.MplWidget.canvas.axes.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M:%S'))
        self.MplWidget.canvas.figure.autofmt_xdate()
        self.MplWidget.canvas.axes.set_xlabel('Log Time')
        self.MplWidget.canvas.axes.set_ylabel('Temperature')

    def apply_rules_to_values(self, vals):
        c1, c2, c3, r = utils.READ_CONST_RESPONSE.split(' ')
        c1 = self.convert_logarithm(c1.split('=')[1])
        c2 = self.convert_logarithm(c2.split('=')[1])
        c3 = self.convert_logarithm(c3.split('=')[1])
        r = int(r.split('=')[1])

        lst = []
        combo_index = self.comboBox_temp_unit.currentIndex()
        for each in vals:
            temp = math.log(r*(1023.0/(each-1)))
            val = 1/(c1+(c2+(c3*temp*temp)) * temp)
            if combo_index == 1:
                val = val*(-272.15)
            lst.append(val)
        return lst

    def convert_logarithm(self, val):
        val, e_val = val.split('e')
        val = float(val)
        e_val = float(e_val)
        res = val*(10**e_val)
        return res

