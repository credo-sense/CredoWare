`serial.serialutil.SerialException: [Errno 13] could not open port /dev/ttyUSB0: [Errno 13] Permission denied: '/dev/ttyUSB0'`

Worked:  
sudo chmod -R 777 /dev/ttyUSB0  

Maybe :  
sudo usermod -a -G tty $USER  
sudo usermod -a -G dialout $USER  

#### Install pyqt5  
https://gist.github.com/ujjwal96/1dcd57542bdaf3c9d1b0dd526ccd44ff  

#### .ui to .py  
`pyuic5 main/main_window.ui > main/main_window.py`

### matplotlib resources  
* https://www.youtube.com/watch?v=2C5VnE9wPhk&t=300s  
* https://yapayzekalabs.blogspot.com/2018/11/pyqt5-gui-qt-designer-matplotlib.html  
* https://matplotlib.org/3.1.1/gallery/user_interfaces/embedding_in_qt_sgskip.html  
* https://pythonspot.com/pyqt5-file-dialog/  
* https://stackoverflow.com/questions/45953770/creating-and-writing-to-a-pdf-file-in-python  
* https://www.youtube.com/watch?v=qiPS70TSvBk  
