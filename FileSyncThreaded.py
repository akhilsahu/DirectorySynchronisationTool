import json
import multiprocessing
import os
import queue
import shutil
import sys
import threading
import time
from datetime import datetime
from multiprocessing.pool import ThreadPool, Pool
from os import listdir
from os.path import isfile, join
import re

from PySide2.QtCore import QObject, Signal, QUrl, QThread
from collections import defaultdict

fileQueue = queue.Queue()
"""This file is not used here. Supports threaded process for copying files"""

class FileSyncThreaded(QObject):
    copy_status = Signal(str)
    progress_bar = Signal(int)
    json_file_link = Signal(str)
    lock = threading.Lock()
    pool_lock = multiprocessing.Lock()

    def __init__(self, src: 'list', dst: 'str'):
        QObject.__init__(self)

        self.input_directory = src
        self.destination = dst + "/"
        self.json_dict = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list)))))
        self.copy_flag = True
        self.source_size = 0
        self.calculateSourceSize()
        self.fileQueue = queue.Queue()
        self.total_files = 0
        self.copied_files = 0
        self.thread_pool = ThreadPool(processes=16)
        self.thread_set = []
        self.stop_threads = threading.Event()

    def sync(self):

        if not self.check_exist(self.destination, "destination"):
            return
        files = self.generate_file_list()
        self.total_files = len(files)
        print(files)
        self.totalFiles = len(files)
        self.threadPoolWorkerCopy(files)
        #self.threadWorkerCopy(files)
        self.generate_json_file()

    def threadWorkerCopy(self, files):

        for _ in range(len(files)):
            t = threading.Thread(target=self.process_files_worker)
            t.daemon = True
            t.start()
            self.thread_set.append(t)

        print(" in  {}".format(files))
        for f in files:
            fileQueue.put(f)
        fileQueue.join()

    def kill_thread(self):
        print("Thread killing")
        self.stop_threads.set()

    def threadPoolWorkerCopy(self, files):

        self.eventEmit(
            "<span style=\" font-size:8pt; font-weight:600; color:blue;\" >initiating copying {} files</span>".format(
                len(files)))

        self.thread_pool.map(self.threadPool_files_worker_instance, files)

    def kill_thread_pool(self):

        self.thread_pool.terminate()
        self.eventEmit("Cancellation: Initiated")
        # self.thread_pool.join()
        self.eventEmit("Cancellation: Done")

    def threadPool_files_worker_instance(self, ff):
        base_path, f = ff
        # ime.sleep(7)
        if self.validate_file_regex(f):
            self.eventEmit("Processing in " + base_path + " file : " + f)
            with self.pool_lock:
                self.progress()
            destination_path, source_path = self.generate_new_file_path(f, base_path)
            self.copy_files(source_path, destination_path)

        else:
            self.eventEmit(
                "<span style=\" font-size:8pt; font-weight:600; color:red;\" >" + "invalid Name Format. Skipping in " + base_path + " file : " + f + "</span>")

    def process_files_worker(self):
        while True:
            base_path, f = fileQueue.get()
            print("----------->FILE====>", f)

            if self.validate_file_regex(f):
                self.eventEmit("Processing in " + base_path + " file : " + f)
                destination_path, source_path = self.generate_new_file_path(f, base_path)

                self.copy_files(source_path, destination_path)
                # time.sleep(6)

            fileQueue.task_done()
            with self.lock:
                self.progress()
            is_killed = self.stop_threads.wait()
            if is_killed:
                break
        print("Killing Thread")

    def generate_file_list(self):

        files = [(dire, f) for dire in self.input_directory if self.check_exist(dire, "source") for f in listdir(dire)]
        return files

    def generate_json_file(self):
        with open('result.json', 'w') as fp:
            json.dump(self.json_dict, fp)
            url = bytearray(QUrl.fromLocalFile(
                self.destination + "result.json").toEncoded()).decode()
            text = "<a href={}>{}</a>".format(url, url)
            self.json_file_link.emit("JSON MANIFEST FILE: " + text)

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

        try:
            progress_percent = (dst_size / src_size) * 100
        except ZeroDivisionError:
            progress_percent = 100
        self.eventEmit(str(round(progress_percent)) + "% complete")
        self.progress_bar.emit(round(progress_percent))

    def copy_files(self, source_path, destination_path):
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        shutil.copy(source_path, destination_path)
        self.copied_files += 1
        self.eventEmit(
            "Copying {} of {} from Source: {} to Destination: {}".format(self.copied_files, self.total_files,
                                                                         source_path, destination_path))

    def check_exist(self, path, emit_type=""):
        status = os.path.exists(path)
        if not status:
            self.eventEmit("Skipping {} path {} Does not Exist".format(emit_type, path))
        return status

    @staticmethod
    def date_from_file(file_name):
        try:
            mtime = os.path.getmtime(file_name)
        except OSError:
            mtime = 0
        return datetime.fromtimestamp(mtime).strftime('%Y%m%d%H%M')

    @staticmethod
    def validate_file_regex(f):
        # "PROJECTNAME_SHOTNAME_TASKNAME.FRAMENUMBER.FILETYPE
        pattern = "[a-zA-Z]\_[a-zA-Z]+\_[a-zA-Z]+\.[0-9]{4}\.[a-zA-Z]+"
        return re.search(pattern, f)

    def clean_destination(self):
        shutil.rmtree(self.destination)
        self.eventEmit("Clean up directories")

#
# fds = FileSyncThreaded(["E:/test/source1", "E:/test/source2"], "E:/test/destination")
# fds.sync()
