import time

from PySide2.QtCore import Qt, Slot

from PySide2.QtWidgets import QApplication, QWidget, QPushButton, QMessageBox, \
    QGridLayout, QFileDialog, QTextEdit, QLineEdit, QSpacerItem, QSizePolicy, QProgressBar, \
    QLabel, QListView, QAbstractItemView, QTreeView
import sys


from directorysync.FileSyncProcess import FileSyncProcess


class Window(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Directory Sync Tool")
        self.setGeometry(200, 200, 700, 700)
        self.sourceFilePath, self.sourceBtn = self.createSourceSelect("source")
        self.destinationFilePath, self.destinationBtn = self.createSourceSelect("destination")
        self.executeButton = QPushButton("Execute")
        self.cancelButton = QPushButton("Cancel")
        self.clearLogButton = QPushButton("Clear Log", self)
        self.myQLabel = QLabel()
        self.progressbar = QProgressBar()
        self.progressbar.setMinimum(0)
        self.progressbar.setMaximum(100)
        self.textEdit = QTextEdit()
        self.textEdit.setReadOnly(True)
        self.createGridLayout()
        self.source = []
        self.destination = ""
        self.executeButton.clicked.connect(self.execute)
        self.cancelButton.clicked.connect(self.cancel_copy)
        self.clearLogButton.clicked.connect(self.clear_log)
    def createGridLayout(self):

        """Create grid layout here"""

        gridLayout = QGridLayout()
        gridLayout.addWidget(self.sourceFilePath, 0, 0, 1, 1)
        gridLayout.addWidget(self.sourceBtn, 0, 1, 1, 1)
        gridLayout.addWidget(self.destinationFilePath, 1, 0, 1, 1)
        gridLayout.addWidget(self.destinationBtn, 1, 1, 1, 1)
        gridLayout.addWidget(self.executeButton, 2, 0, 1, 1)
        gridLayout.addWidget(self.cancelButton, 2, 1, 1, 1)

        gridLayout.addWidget(self.textEdit, 5, 0, 7, 2)
        gridLayout.addWidget(self.clearLogButton, 12, 1)
        gridLayout.addWidget(self.progressbar, 14, 0, 1, 2)
        gridLayout.addWidget(self.myQLabel, 16, 0)


        vspacer = QSpacerItem(
            QSizePolicy.Minimum, QSizePolicy.Expanding)
        gridLayout.addItem(vspacer, 0, 0, Qt.AlignTop)


        self.setLayout(gridLayout)

    def createSourceSelect(self, init_text):
        filePath = QLineEdit()
        filePath.setPlaceholderText("Choose " + init_text + " folder")
        filePath.setDisabled(True)
        btn = QPushButton("Browse", self)
        if init_text == "source":
            btn.clicked.connect(lambda: self.getMultipleSelected(init_text))
        else:
            btn.clicked.connect(lambda: self.getSeletedFile(init_text))
        return filePath, btn

    def execute(self):
        if len(self.source) > 0 and len(self.destination) > 0:
            self.executeButton.setEnabled(False)
            #self.fds = FileSynchronizer(self.source, self.destination)
            #self.fds = FileSyncThreaded(self.source, self.destination)
            self.fds = FileSyncProcess(self.source, self.destination)
            self.fds.copy_status.connect(self.copy_status)
            self.fds.progress_bar.connect(self.progress_bar)
            self.fds.json_file_link.connect(self.json_file_link)
            self.fds.sync()
            self.executeButton.setEnabled(True)
            self.cancelButton.setEnabled(True)

    @Slot(str)
    def json_file_link(self, data):
        self.myQLabel.setText(data)
        self.myQLabel.setOpenExternalLinks(True)

    @Slot(int)
    def progress_bar(self, pr):
        print(pr)
        self.progressbar.setValue(pr)

    @Slot()
    def copy_status(self, status):
        self.textEdit.append(status)

        print(status)

    def cancel_copy(self):
        self.fds.kill_process()  # File Sync Process
        self.fds.kill_thread()  #kill thread multiple
        # self.fds.kill_thread_pool() # kill thread pool
        #self.fds.copy_flag = False

        self.executeButton.setEnabled(True)
        self.cancelButton.setEnabled(True)

        userInfo = QMessageBox.question(self, "Confirmation",
                                        "Clean up destination directory? Warning: Entire directory may be deleted in this process",
                                        QMessageBox.Yes | QMessageBox.No)

        if userInfo == QMessageBox.Yes:
            self.fds.clean_destination()

        elif userInfo == QMessageBox.No:
            pass

    def clear_log(self):
        self.textEdit.clear()

    def getSeletedFile(self, init_text):
        path = QFileDialog.getExistingDirectory()
        self.destination = path
        eval("self." + init_text + "FilePath").setText(path)

    def getMultipleSelected(self, init_text):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.DirectoryOnly)
        file_dialog.setOption(QFileDialog.DontUseNativeDialog, True)
        file_view = file_dialog.findChild(QListView, 'listView')

        # to make it possible to select multiple directories:
        if file_view:
            file_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        f_tree_view = file_dialog.findChild(QTreeView)
        if f_tree_view:
            f_tree_view.setSelectionMode(QAbstractItemView.ExtendedSelection)

        if file_dialog.exec():
            self.source = file_dialog.selectedFiles()
            eval("self." + init_text + "FilePath").setText(",".join(self.source))
            print(self.source)

if __name__=="__main__":
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    app.exec_()
    sys.exit(0)
