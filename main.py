from flask import Flask, render_template, request, make_response
from PyQt5 import QtCore, QtGui, QtWidgets
import configparser
import qrcode
import datetime
import os
import sys
import threading
import json
import requests
import time
import asyncio


GUI_APP = 'MainWindow()'
SETTINGS_INI = {"set_host": "0,0,0,0", "set_port": "8044", "qr_path": "", "max_log_index": 200,
                "qr_log_path": "./qr_logs/"}
FONT_COLOR = False
ITEMS_CREATE = 0


def loggers(text, status=0):
    """ Функция логировани в файл и вывода в GUI \n
        описание переменной status \n
        0 = SUCCESS \n
        1 = ERROR \n
        2 = EVENT \n
        3 = WARNING \n
    """
    global GUI_APP
    global FONT_COLOR
    global SETTINGS_INI

    path_log = SETTINGS_INI["qr_log_path"]

    try:
        if os.path.exists(path_log):
            pass
        else:
            os.makedirs(path_log)
    except:
        pass

    today = datetime.datetime.today()

    for_file_name = str(today.strftime("%Y-%m-%d"))

    # определяем цвет лога
    color_s = "white"
    if status == 1:
        color_s = "red"
    elif status == 2:
        if FONT_COLOR:
            color_s = "light blue"
            FONT_COLOR = False
        else:
            FONT_COLOR = True
            color_s = "sky blue"

    elif status == 3:
        color_s = "orange"

    # Создаем лог
    mess = str(today.strftime("%Y-%m-%d-%H.%M.%S")) + "\t" + text + "\n"

    # Открываем и записываем логи в файл отчета.
    with open(f'{path_log}{for_file_name}-QR_LOG.log', 'a', encoding='utf-8') as file:
        file.write(mess)
    # Вызываем через глобальную метод класса интерфейса
    GUI_APP.add_log(f"<font color=\"{color_s}\">{mess}")

    return True
# ---------------------------------------------------------------------------


def take_settings():
    """ Функция получения настройки из файла settings.ini. """
    # Перестрахуемся если файл функции не подгрузится
    global SETTINGS_INI
    settings_ini = SETTINGS_INI

    settings_file = configparser.ConfigParser()

    error_mess = "ошибка загрузки данных из settings.ini"

    # проверяем файл settings.ini
    if os.path.isfile("settings.ini"):
        try:
            settings_file.read("settings.ini", encoding="utf-8")
            settings_ini["set_host"] = settings_file["GEN"]["HOST"]
            settings_ini["set_port"] = settings_file["GEN"]["PORT"]
            settings_ini["qr_path"] = settings_file["GEN"]["QR_PATH"]
            settings_ini["qr_log_path"] = settings_file["GEN"]["PATH_LOG"]
            settings_ini["max_log_index"] = int(settings_file["GEN"]["MAX_LOG_INDEX"])
        except KeyError:
            loggers(f"ERROR\t{take_settings.__name__}\t Exception: {KeyError} {error_mess}", 1)  # log
            print(error_mess)
            raise
        except Exception:
            loggers(f"ERROR\t{take_settings.__name__}\t Exception: {Exception} {error_mess}", 1)  # log
            print(error_mess)
            raise
    else:
        loggers(f"WARNING\t{take_settings.__name__}\t Файл settings.ini не найден в системе, "
                f"продолжена работа с host 0,0,0,0 и port 8044", 3)  # log
        print("Файл settings.ini не найден в системе, продолжена работа с host 0,0,0,0 и port 8044")

    return settings_ini


def gen_qr_code(user_id, user_ic, qr_path):
    """ генератор QR кодов принимает ID пользователя, номер заявки и адрес папки куда сохранять файл. """
    global ITEMS_CREATE
    # проверяем наличие папки указаной в настройках и создаем если её нет
    try:
        if not os.path.exists(qr_path) and len(qr_path) != 0:
            loggers(f"EVENT\t{gen_qr_code.__name__}\t Была создана директория {qr_path}", 2)  # log
            os.makedirs(qr_path)
            time.sleep(0.2)
    except:
        loggers(f"ERROR\t{gen_qr_code.__name__}\t Ошибка создания или обращения к {qr_path}", 1)  # log

    # создаем имя с указанием куда сохранять в виде строки
    filename = f"{qr_path}{user_id}_{user_ic}.png"

    # генерируем qr код и сохраняем
    img = qrcode.make(f"{user_id}_{user_ic}")

    try:
        img.save(filename)
        ITEMS_CREATE += 1
        loggers(f"EVENT\t{gen_qr_code.__name__}\t Был создан файл {filename}", 2)  # log
        return True
    except:
        loggers(f"WARNING\t{gen_qr_code.__name__}\t Не удалось проверить файл {filename}", 3)  # log
        return False

# -------------------------------------------------------------------------------------------


def qr_flask():
    """ Главная функция создания сервера Фласк.
    По стандарту сервер фласк будет создаваться на local с портом 8044
    """
    global SETTINGS_INI

    app = Flask(__name__)   # Обьявления сервера
    print("Hello I'm QR_Flask")
    loggers(f"SUCCESS\t{qr_flask.__name__}\t Hello I'm QR_CODE_server")  # log

    # Функция приема ответа сервера
    @app.route('/ShowQR/', methods=['GET', 'POST'])
    def create_qr_code():
        if request.method == "POST":  # Если POST тогда принимаем данные
            qr_path = SETTINGS_INI["qr_path"]

            # Пробуем получить данные из формы
            user_id = request.form.get("f_id")
            user_ic = request.form.get("f_ic")
            # Если нет данных из формы пробуем получить из общего потока **args
            if not user_id:
                user_id = request.args.get("f_id")
                user_ic = request.args.get("f_ic")

            result = gen_qr_code(user_id, user_ic, qr_path)  # Создаем QR код и получаем bool ответ

            status_m = "ERROR"  # Логика: если ответ True будет изменен в SUCCESS
            if result:
                status_m = "SUCCESS"

            return make_response(f"<h2>{status_m}: QR code создан в разделе {qr_path}.")

        elif request.method == "GET":   # Если GET отправляем форму index.html
            if os.path.isfile("./templates/index.html"):
                loggers(f"EVENT\t{create_qr_code.__name__}\t [GET] send to client - index.html", 2)  # log
                try:
                    return render_template("index.html")  # открываем страницу отправки сообщения
                except:
                    loggers(f"ERROR\t{create_qr_code.__name__}\t [GET] ERROR: 500, fail open file index.html.", 1) # log
                    return make_response(f"<h2>Error: 500, fail open file index.html</h2>")
            else:
                loggers(f"ERROR\t{create_qr_code.__name__}\t [GET] file index.html or path ./templates/ not found.", 1)
                return make_response(f"<h2>Error: 400, fail open file index.html</h2>")
        else:
            return make_response(f"<h2>Error: 400, only POST method can be called</h2>")

    @app.route('/test_server/', methods=['GET'])
    def test_qr_server():
        """ Просто функция проверки сервера """
        return make_response("hello")

    # ЗАПУСК СЕРВЕРА С ПАРАМЕТРАМИ  <---------------------------------------------------------------------------<<<
    app.run(debug=False, host=SETTINGS_INI["set_host"], port=int(SETTINGS_INI["set_port"]))

# -------------------------------------------------------------------------------------------


# Окно завершения программы если сервер уже запущен.
class Ui_Dialog_test(object):
    """ Окно завершения программы если сервер уже запущен. """
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(387, 283)
        self.but_yes = QtWidgets.QPushButton(Dialog)
        self.but_yes.setGeometry(QtCore.QRect(140, 180, 91, 51))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.but_yes.setFont(font)
        self.but_yes.setObjectName("but_yes")
        self.label = QtWidgets.QLabel(Dialog)
        self.label.setGeometry(QtCore.QRect(20, 50, 351, 101))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.label.setFont(font)
        self.label.setObjectName("label")

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))
        self.but_yes.setText(_translate("Dialog", "Ok"))
        self.label.setText(_translate("Dialog", "The server is already running. Contact the admin"))


# Окно подтверждения остановки сервера.
class Ui_Dialog(object):
    """ Окно подтверждения остановки сервера. """
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(390, 250)
        Dialog.setMinimumSize(QtCore.QSize(390, 250))
        Dialog.setMaximumSize(QtCore.QSize(390, 250))
        Dialog.setStyleSheet("background-color: rgb(0, 0, 0);")
        self.frame = QtWidgets.QFrame(Dialog)
        self.frame.setGeometry(QtCore.QRect(9, 9, 371, 231))
        self.frame.setStyleSheet("border: 1px solid;\n"
"border-color: rgb(14, 143, 0);")
        self.frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.label = QtWidgets.QLabel(self.frame)
        self.label.setGeometry(QtCore.QRect(30, 20, 291, 81))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.label.setFont(font)
        self.label.setStyleSheet("color: rgb(18, 255, 2);\n"
"border: 1px solid;\n"
"border-color: rgb(14, 143, 0);")
        self.label.setObjectName("label")
        self.but_no = QtWidgets.QPushButton(self.frame)
        self.but_no.setGeometry(QtCore.QRect(30, 150, 111, 21))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.but_no.setFont(font)
        self.but_no.setStyleSheet("QPushButton {\n"
"    border: 0px solid;\n"
"    \n"
"    color: rgb(0, 150, 55);\n"
"}\n"
"QPushButton:hover {\n"
"    color: rgb(0, 200, 55)\n"
"}\n"
"QPushButton:pressed {    \n"
"    color: rgb(0, 255, 55)\n"
"}")
        self.but_no.setObjectName("but_no")
        self.but_yes = QtWidgets.QPushButton(self.frame)
        self.but_yes.setGeometry(QtCore.QRect(30, 120, 111, 21))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.but_yes.setFont(font)
        self.but_yes.setStyleSheet("QPushButton {\n"
"    border: 0px solid;\n"
"    \n"
"    color: rgb(0, 150, 55);\n"
"}\n"
"QPushButton:hover {\n"
"    color: rgb(255, 5, 5);\n"
"}\n"
"QPushButton:pressed {    \n"
"    color: rgb(0, 255, 55)\n"
"}")
        self.but_yes.setObjectName("but_yes")

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))
        self.label.setText(_translate("Dialog", "Остановить сервер QR ?"))
        self.but_no.setText(_translate("Dialog", "Нет <------"))
        self.but_yes.setText(_translate("Dialog", "Да <------"))


# Главное графическое окно программы.
class Ui_MainWindow(object):
    """ Главное графическое окно программы. """
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(997, 618)
        MainWindow.setStyleSheet("background-color: rgb(22, 22, 22);")
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.frame = QtWidgets.QFrame(self.centralwidget)
        self.frame.setMinimumSize(QtCore.QSize(150, 600))
        self.frame.setMaximumSize(QtCore.QSize(150, 16777215))
        self.frame.setStyleSheet("border: 1px solid;\n"
"border-color: rgb(14, 143, 0);")
        self.frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.frame)
        self.verticalLayout.setContentsMargins(1, 1, 1, 1)
        self.verticalLayout.setSpacing(1)
        self.verticalLayout.setObjectName("verticalLayout")
        self.frame_3 = QtWidgets.QFrame(self.frame)
        self.frame_3.setMinimumSize(QtCore.QSize(0, 100))
        self.frame_3.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame_3.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_3.setObjectName("frame_3")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.frame_3)
        self.verticalLayout_2.setContentsMargins(1, -1, 1, -1)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.but_exit = QtWidgets.QPushButton(self.frame_3)
        self.but_exit.setMinimumSize(QtCore.QSize(140, 25))
        self.but_exit.setMaximumSize(QtCore.QSize(140, 25))
        self.but_exit.setStyleSheet("QPushButton {\n"
"    border: 0px solid;\n"
"    \n"
"    color: rgb(0, 150, 55);\n"
"}\n"
"QPushButton:hover {\n"
"    color: rgb(255, 5, 5);\n"
"}\n"
"QPushButton:pressed {    \n"
"    color: rgb(0, 255, 55)\n"
"}")
        self.but_exit.setObjectName("but_exit")
        self.verticalLayout_2.addWidget(self.but_exit)
        self.but_clear = QtWidgets.QPushButton(self.frame_3)
        self.but_clear.setMinimumSize(QtCore.QSize(140, 25))
        self.but_clear.setMaximumSize(QtCore.QSize(140, 25))
        font = QtGui.QFont()
        font.setPointSize(8)
        self.but_clear.setFont(font)
        self.but_clear.setStyleSheet("QPushButton {\n"
"    border: 0px solid;\n"
"    \n"
"    color: rgb(0, 150, 55);\n"
"}\n"
"QPushButton:hover {\n"
"    color: rgb(0, 200, 55)\n"
"}\n"
"QPushButton:pressed {    \n"
"    color: rgb(0, 255, 55)\n"
"}")
        self.but_clear.setObjectName("but_clear")
        self.verticalLayout_2.addWidget(self.but_clear)
        self.but_check = QtWidgets.QPushButton(self.frame_3)
        self.but_check.setMinimumSize(QtCore.QSize(140, 25))
        self.but_check.setMaximumSize(QtCore.QSize(140, 25))
        font = QtGui.QFont()
        font.setPointSize(8)
        self.but_check.setFont(font)
        self.but_check.setStyleSheet("QPushButton {\n"
"    border: 0px solid;\n"
"    \n"
"    color: rgb(0, 150, 55);\n"
"}\n"
"QPushButton:hover {\n"
"    color: rgb(0, 200, 55)\n"
"}\n"
"QPushButton:pressed {    \n"
"    color: rgb(0, 255, 55)\n"
"}")
        self.but_check.setObjectName("but_check")
        self.verticalLayout_2.addWidget(self.but_check)
        self.verticalLayout.addWidget(self.frame_3, 0, QtCore.Qt.AlignTop)
        self.frame_5 = QtWidgets.QFrame(self.frame)
        self.frame_5.setStyleSheet("border: 0px solid;")
        self.frame_5.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame_5.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_5.setObjectName("frame_5")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.frame_5)
        self.verticalLayout_4.setContentsMargins(2, 2, 2, -1)
        self.verticalLayout_4.setSpacing(2)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.label_message = QtWidgets.QLabel(self.frame_5)
        self.label_message.setStyleSheet("border: 0px solid;\n"
"    \n"
"color: rgb(0, 150, 55);")
        self.label_message.setText("")
        self.label_message.setObjectName("label_message")
        self.verticalLayout_4.addWidget(self.label_message)
        self.label_host = QtWidgets.QLabel(self.frame_5)
        self.label_host.setMinimumSize(QtCore.QSize(140, 20))
        self.label_host.setMaximumSize(QtCore.QSize(140, 30))
        self.label_host.setStyleSheet("border: 0px solid;\n"
"    \n"
"color: rgb(255, 105, 0);")
        self.label_host.setObjectName("label_host")
        self.verticalLayout_4.addWidget(self.label_host)
        self.label_port = QtWidgets.QLabel(self.frame_5)
        self.label_port.setMinimumSize(QtCore.QSize(140, 30))
        self.label_port.setMaximumSize(QtCore.QSize(140, 30))
        self.label_port.setStyleSheet("border: 0px solid;\n"
"    \n"
"color: rgb(255, 105, 0);")
        self.label_port.setObjectName("label_port")
        self.verticalLayout_4.addWidget(self.label_port)
        self.frame_6 = QtWidgets.QFrame(self.frame_5)
        self.frame_6.setMinimumSize(QtCore.QSize(140, 30))
        self.frame_6.setMaximumSize(QtCore.QSize(140, 30))
        self.frame_6.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame_6.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_6.setObjectName("frame_6")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.frame_6)
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_2.setSpacing(0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label_file_plus = QtWidgets.QLabel(self.frame_6)
        self.label_file_plus.setMinimumSize(QtCore.QSize(90, 30))
        self.label_file_plus.setMaximumSize(QtCore.QSize(90, 30))
        self.label_file_plus.setStyleSheet("border: 0px solid;\n"
"    \n"
"color: rgb(0, 150, 55);")
        self.label_file_plus.setObjectName("label_file_plus")
        self.horizontalLayout_2.addWidget(self.label_file_plus)
        self.label_file_index = QtWidgets.QLabel(self.frame_6)
        self.label_file_index.setStyleSheet("border: 0px solid;\n"
"    \n"
"color: rgb(0, 150, 55);")
        self.label_file_index.setObjectName("label_file_index")
        self.horizontalLayout_2.addWidget(self.label_file_index)
        self.verticalLayout_4.addWidget(self.frame_6)
        self.verticalLayout.addWidget(self.frame_5)
        self.frame_4 = QtWidgets.QFrame(self.frame)
        self.frame_4.setMinimumSize(QtCore.QSize(0, 200))
        self.frame_4.setMaximumSize(QtCore.QSize(16777215, 200))
        self.frame_4.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame_4.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_4.setObjectName("frame_4")
        self.but_status = QtWidgets.QPushButton(self.frame_4)
        self.but_status.setGeometry(QtCore.QRect(120, 180, 21, 21))
        self.but_status.setStyleSheet("QPushButton {\n"
"    border: 0px solid;\n"
"    \n"
"    background-color: rgb(255, 1, 1);\n"
"    color: rgb(0, 150, 55);\n"
"}")
        self.but_status.setObjectName("but_status")
        self.but_en_ru = QtWidgets.QPushButton(self.frame_4)
        self.but_en_ru.setGeometry(QtCore.QRect(10, 150, 41, 41))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.but_en_ru.setFont(font)
        self.but_en_ru.setStyleSheet("color: rgb(218, 218, 218);")
        self.but_en_ru.setObjectName("but_en_ru")
        self.label_qr_image = QtWidgets.QLabel(self.frame_4)
        self.label_qr_image.setGeometry(QtCore.QRect(10, 10, 126, 126))
        self.label_qr_image.setMinimumSize(QtCore.QSize(126, 126))
        self.label_qr_image.setMaximumSize(QtCore.QSize(126, 126))
        self.label_qr_image.setObjectName("label_qr_image")
        self.checkBox_scroll = QtWidgets.QCheckBox(self.frame_4)
        self.checkBox_scroll.setGeometry(QtCore.QRect(60, 150, 81, 17))
        self.checkBox_scroll.setStyleSheet("color: rgb(0, 150, 55);")
        self.checkBox_scroll.setObjectName("checkBox_scroll")
        self.verticalLayout.addWidget(self.frame_4)
        self.horizontalLayout.addWidget(self.frame)
        self.frame_2 = QtWidgets.QFrame(self.centralwidget)
        self.frame_2.setMinimumSize(QtCore.QSize(600, 600))
        self.frame_2.setStyleSheet("border: 1px solid;\n"
"border-color: rgb(14, 143, 0);")
        self.frame_2.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame_2.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_2.setObjectName("frame_2")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.frame_2)
        self.verticalLayout_3.setContentsMargins(2, 2, 2, 1)
        self.verticalLayout_3.setSpacing(1)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.text_logs = QtWidgets.QTextBrowser(self.frame_2)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.text_logs.setFont(font)
        self.text_logs.setObjectName("text_logs")
        self.verticalLayout_3.addWidget(self.text_logs)
        self.label_status = QtWidgets.QLabel(self.frame_2)
        self.label_status.setMinimumSize(QtCore.QSize(0, 20))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.label_status.setFont(font)
        self.label_status.setStyleSheet("color: rgb(18, 255, 2);")
        self.label_status.setObjectName("label_status")
        self.verticalLayout_3.addWidget(self.label_status)
        self.horizontalLayout.addWidget(self.frame_2)
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.but_exit.setText(_translate("MainWindow", "-- Выход --"))
        self.but_clear.setText(_translate("MainWindow", "-- Очистить --"))
        self.but_check.setText(_translate("MainWindow", "-- Тест сервера --"))
        self.label_host.setText(_translate("MainWindow", "Host: 0.0.0.0"))
        self.label_port.setText(_translate("MainWindow", "Port: 0000"))
        self.label_file_plus.setText(_translate("MainWindow", "Файлов создано:"))
        self.label_file_index.setText(_translate("MainWindow", "0"))
        self.but_status.setText(_translate("MainWindow", "1"))
        self.but_en_ru.setText(_translate("MainWindow", "RU"))
        self.label_qr_image.setText(_translate("MainWindow", "TextLabel"))
        self.checkBox_scroll.setText(_translate("MainWindow", "AutoScroll"))
        self.label_status.setText(_translate("MainWindow", "Статус:"))


class MainWindow(QtWidgets.QMainWindow):

    def thread_qr_flask(self):
        qr_flask()

    def __init__(self):
        super().__init__()
        print("Hallo i'm PyQt")

        self.block_append_log = True

        # СОЗДАНИЕ ПОТОКА ДЛЯ СЕРВЕРА FLASK <-------------------------------------------------------------------<<<
        self.thread_for_flask = threading.Thread(target=self.thread_qr_flask, name="QR_code_server")

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle("QR code creator")

        self.log_index = 0  # Счесчик логов
        self.max_log_index = 100  # Максимальное кол-во для интерфейса (получается из settings.ini)

        self.ui.checkBox_scroll.toggle()    # Ставим галочку на автоскрол
        # tray_icon -------------------------------------------------
        self.tray_icon = QtWidgets.QSystemTrayIcon()
        self.tray_icon.setToolTip("VIG QR code server")
        # Create the icon
        icon = QtGui.QIcon("icon.png")
        self.tray_icon.setIcon(icon)  # self.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon))

        self.it_hide = False
        self.show_action = QtWidgets.QAction("Показать/скрыть", self)
        self.quit_action = QtWidgets.QAction("Выход", self)

        # hide_action = QtWidgets.QAction("Hide", self)
        self.show_action.triggered.connect(self.show_hide)
        # hide_action.triggered.connect(self.hide)
        self.quit_action.triggered.connect(self.close_server)  # QtWidgets.qApp.quit)

        tray_menu = QtWidgets.QMenu()
        tray_menu.addAction(self.show_action)
        # tray_menu.addAction(hide_action)
        tray_menu.addAction(self.quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        # -----------------------------------------------------------
        # BUTTONS ---------------------------------------------------
        self.ui.label_qr_image.setPixmap(QtGui.QPixmap("qr_text_pix.png"))
        self.ui.but_exit.clicked.connect(self.close_server)
        self.ui.but_clear.clicked.connect(self.clear_logs)
        self.ui.but_check.clicked.connect(self.test_server)
        # -----------------------------------------------------------

    def test_server(self):
        """ Проверяет поток созданный для сервера """
        if self.thread_for_flask.is_alive():
            self.ui.but_status.setStyleSheet("QPushButton {\n"
                                                "    border: 0px solid;\n"
                                                "    \n"
                                                "    background-color: rgb(18, 255, 2);\n"
                                                "    color: rgb(0, 150, 55);\n"
                                                "}")
            self.ui.label_status.setText("Status: server online!")
        else:
            self.ui.but_status.setStyleSheet("QPushButton {\n"
                                                "    border: 0px solid;\n"
                                                "    \n"
                                                "    background-color: rgb(255, 1, 1);\n"
                                                "    color: rgb(0, 150, 55);\n"
                                                "}")
            self.ui.label_status.setText("Status: server OFFLINE!")

    def test_port(self):
        """ тест сервера фласк (проверяет ответ из порта) """
        global SETTINGS_INI

        port_info = SETTINGS_INI["set_port"]
        try:
            # вызывает исключение если данный порт никем не занят
            response = requests.get(f"http://127.0.0.1:{port_info}/test_server/")
            loggers(f"ERROR\t{MainWindow.__name__}\t Порт {port_info} уже занят другим севером", 1)  # log
        except:
            pass

    def test_server_run(self):
        """ Вызываем окно закрытия программы если порт занят другим сервером"""
        try:
            global SETTINGS_INI

            port_info = SETTINGS_INI["set_port"]

            # вызывает исключение если данный порт никем не занят
            requests.get(f"http://127.0.0.1:{port_info}/test_server/")
        except:
            return  # завершает функцию без вызова окна завершения программы

        # создаем окно завершения программы --------------------------------
        Dialog = QtWidgets.QDialog()
        ui2 = Ui_Dialog_test()
        ui2.setupUi(Dialog)
        ui2.but_yes.clicked.connect(self.exit_def)

        Dialog.exec_()
        # ------------------------------------------------------------------

    def clear_logs(self):
        """ Метод можно вызвать только из самого класса """
        self.ui.text_logs.clear()

    def show_hide(self):

        if self.it_hide:
            self.it_hide = False
            self.show()
        else:
            self.it_hide = True
            self.hide()

    def close_server(self):
        """ Вызываем окно подтверждения закрытия сервера """
        Dialog = QtWidgets.QDialog()
        ui2 = Ui_Dialog()
        ui2.setupUi(Dialog)
        ui2.but_yes.clicked.connect(self.exit_def)
        ui2.but_no.clicked.connect(Dialog.hide)

        Dialog.exec_()

    def load_settings_file(self):
        global SETTINGS_INI
        self.max_log_index = int(SETTINGS_INI["max_log_index"])

    # ФУНКЦИЯ ЗАПУСКА ПОТОКА С СЕРВЕРОМ ФЛАСК <---------------------------------------------------------------<<<
    def start_server(self):
        """ Запускает сервер в потоке """
        self.thread_for_flask.start()

        port_info = SETTINGS_INI["set_port"]
        host_info = SETTINGS_INI["set_host"]

        self.ui.label_host.setText(f"Host: {host_info}")
        self.ui.label_port.setText(f"Port: {port_info}")

        loggers(f"EVENT\t{MainWindow.__name__}\t Server started: host= {host_info}, port= {port_info}", 3)  # log

    def closeEvent(self, event):
        """ Блокирует системную кнопку закрытия программы и сворачивает в трэй  """
        event.ignore()
        self.hide()
        self.it_hide = True

    def exit_def(self):
        """ Остановка программы где проверяется наличие потока фласк """
        if self.thread_for_flask.is_alive():  # проверяет наличие потока с сервером
            self.thread_for_flask.start()  # повторный запуск вызывает остановку сервера, закрытие потока и программы
        else:
            sys.exit()

    def add_log(self, text_log):
        """ Функция добавляет логи в интерфейс и чистит логи по достижению значения (self.max_log_index). """
        # self.read_log_file()
        global ITEMS_CREATE

        # self.log_index += 1  # Наблюдается перегрузка окна скорость обратно пропорциональна ко-ву записей

        if self.block_append_log:
            self.block_append_log = False
        else:
            return

        self.ui.label_file_index.setText(str(ITEMS_CREATE))  # Счетчик созданных файлов за сессию
        time.sleep(0.001)
        self.log_index += 1  # Наблюдается перегрузка окна скорость обратно пропорциональна ко-ву записей
        # self.log_index += 1  # Плохая идея при большей скорости заполнять полностью окно логов

        if self.log_index < int(self.max_log_index):
            # метод append для QtextBrowser не асинхронный и вызывает падение программы при параллельном вызове
            self.ui.text_logs.append(str(text_log))
            time.sleep(0.001)   # СПАСАЕТ ОТ ПЕРЕГРУЗКИ ОКНА ВЫВОДА ЛОГОВ <-------------------------------------<<<
            # Проверяем нужен ли скроллинг сообщений в конец.
            if self.ui.checkBox_scroll.isChecked():
                scroll_bar = self.ui.text_logs.verticalScrollBar()
                scroll_bar.setValue(4000)
        elif self.log_index >= int(self.max_log_index):
            self.log_index = 0
            self.ui.but_clear.click()

        self.block_append_log = True


def main():
    global GUI_APP
    global SETTINGS_INI

    SETTINGS_INI = take_settings()  # Загрузка данных параметров

    # Обьявление графического интерфейса
    app_gui = QtWidgets.QApplication(sys.argv)
    app_gui.setWindowIcon(QtGui.QIcon("icon.png"))
    # Создание интерфейса
    GUI_APP = MainWindow()

    GUI_APP.show()

    GUI_APP.load_settings_file()
    GUI_APP.test_server_run()
    GUI_APP.start_server()

    sys.exit(app_gui.exec())


if __name__ == "__main__":
    main()


# pyuic5 -x dialog_yes_no.ui -o dialog_yes_no.py
# pyuic5 -x dialog_yes_no_ru.ui -o dialog_yes_no_ru.py
# pyuic5 -x qr_gui.ui -o qr_gui.py
# pyuic5 -x qr_gui_ru.ui -o qr_gui_ru.py
# auto-py-to-exe
