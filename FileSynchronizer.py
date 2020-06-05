import json
import os
import queue
import shutil
import threading
from datetime import datetime
from os import listdir
from os.path import isfile, join
import re

from PySide2.QtCore import QObject, Signal, Slot, QUrl
from collections import defaultdict


class FileSynchronizer(QObject):
    copy_status = Signal(str)
    progress_bar = Signal(int)
    json_file_link = Signal(str)
    def __init__(self, src: 'list', dst: 'str'):
        QObject.__init__(self)
        self.input_directory = src
        self.destination = dst + "/"
        self.json_dict = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list)))))
        self.copy_flag = True
        self.source_size = 0
        self.calculateSourceSize()


    def sync(self):
        print("Reading source directories" + self.destination)
        if not self.check_exist(self.destination):
            self.eventEmit(
                "<span style=\" font-size:8pt; font-weight:600; color:red;\" >" + "Invalid Destination Folder. Please check and verify" + "</span>")
            return

        for dir in self.input_directory:
            if self.check_exist(dir) and self.copy_flag:
                files = [f for f in listdir(dir)]
                print(files)

                self.process_files(dir, files)
            else:
                self.eventEmit("Skipping source path " + dir + " Does not Exist")
        self.generate_json_file()

    def process_files(self, base_path, files):

        for f in files:
            self.eventEmit("Processing in " + base_path + " file : " + f)

            if self.validate_file(f):
                split__ = f.split("_")
                destination_path, source_path = self.generate_new_file_path(f, base_path)
                self.copy_files(source_path, destination_path)
                self.progress()
                # self.json_dict[split__[0]][yyyymmddhhmm][split__[0] + "_" + split__[
                #     1]][split_dot[0]][split_dot[2]].append(f)
            else:
                self.eventEmit("<span style=\" font-size:8pt; font-weight:600; color:red;\" >"+"invalid Name Format. Skipping in " + base_path + " file : " + f+"</span>")

    def generate_json_file(self):
        with open('result.json', 'w') as fp:
            json.dump(self.json_dict, fp)
            url = bytearray(QUrl.fromLocalFile(
                    self.destination + "result.json").toEncoded()).decode()
            text = "<a href={}>{}</a>".format(url,url)
            self.json_file_link.emit("JSON MANIFEST FILE: "+ text)

    def generate_new_file_path(self, f, base_path):
        split__ = f.split("_")
        yyyymmddhhmm = self.date_from_file(base_path + "/" + f)

        split_dot = split__[2].split(".")

        destination_base_path = self.destination + split__[0] + "/"

        self.json_dict[split__[0]][yyyymmddhhmm][split__[0] + "_" + split__[
            1]][split_dot[0]][split_dot[2]].append(f)

        destination_path = destination_base_path + yyyymmddhhmm + "/" + split__[0] + "_" + split__[
            1] + "/" + split_dot[0] + "/" + split_dot[2] + "/" + f
        source_path = base_path + "/" + f
        return destination_path, source_path

    def calculateSourceSize(self):
        for i in self.input_directory:
            self.source_size += (sum(
                os.path.getsize(os.path.join(dirpath, filename)) for dirpath, dirnames, filenames in os.walk(i) for
                filename in filenames))

    def eventEmit(self, msg):
        print(msg)
        self.copy_status.emit(msg)

    def progress(self):

        src_size = self.source_size
        dst_size = (sum(
            os.path.getsize(os.path.join(dirpath, filename)) for dirpath, dirnames, filenames in
            os.walk(self.destination) for
            filename in filenames))
        progress_percent = (dst_size / src_size) * 100

        self.eventEmit(str(round(progress_percent)) + "% complete")
        self.progress_bar.emit(round(progress_percent))

    @staticmethod
    def copy_files(source_path, destination_path):
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        shutil.copy(source_path, destination_path)

    @staticmethod
    def check_exist(path):
        return os.path.exists(path)

    @staticmethod
    def date_from_file(file_name):
        try:
            mtime = os.path.getmtime(file_name)
        except OSError:
            mtime = 0
        return  datetime.fromtimestamp(mtime).strftime('%Y%m%d%H%M')

    @staticmethod
    def validate_file(f):
        # "PROJECTNAME_SHOTNAME_TASKNAME.FRAMENUMBER.FILETYPE
        pattern = "[a-zA-Z]\_[a-zA-Z]+\_[a-zA-Z]+\.[0-9]{4}\.[a-zA-Z]+"
        return re.search(pattern, f)

    def clean_destination(self):
        shutil.rmtree(self.destination)
        print("Clean up directories")

#
fds = FileSynchronizer(["E:/test/source1"], "E:/test/destination")
fds.sync()
