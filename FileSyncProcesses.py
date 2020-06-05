import json
import multiprocessing, queue
import os
import shutil
import threading

from datetime import datetime
from functools import reduce
from multiprocessing.pool import Pool
from os import listdir
import re
from PySide2.QtCore import QObject, Signal, QUrl
from collections import defaultdict


class FileSyncProcess(QObject):
    json_dict = defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list)))))
    total_files = 0
    copied_files = 0
    source_size = 0
    copy_status = Signal(str)
    progress_bar = Signal(int)
    json_file_link = Signal(str)

    def __init__(self, src: 'list', dst: 'str'):
        QObject.__init__(self)
        self.stop_threads=threading.Event()
        self.all_processes = []
        self.input_directory = src
        self.destination = dst + "/"
        self.source_size = 0
        self.calculateSourceSize()
        self.p = Pool()
        self.fileQueue = multiprocessing.Queue()
        self.resultQueue = multiprocessing.Queue()

    def sync(self):

        if not self.check_exist(self.destination, "destination"):
            return
        files = self.generate_file_list()
        FileSyncProcess.total_files = len(files)
        self.processWorkerCopy(files)
        # self.generate_json_file()

    def processWorkerCopy(self, files):
        print(files)
        self.eventEmit(
            "<span style=\" font-size:8pt; font-weight:600; color:blue;\" >initiating copying {} files</span>".format(
                len(files)))

        for f in files:
            self.fileQueue.put(f)

        for i in range(0, self.fileQueue.qsize()):
            process = multiprocessing.Process(target=self.process_files_worker_queue,
                                              args=(self.fileQueue, self.resultQueue))
            t = threading.Thread(target=self.process_result_worker)


            process.start()
            t.start()
            self.all_processes.append(process)

        # for _ in range(0, self.fileQueue.qsize()):
        #     print("Threads started")
        #     t = threading.Thread(target=self.process_result_worker)
        #
        #     t.start()

        # for f in self.p.imap_unordered(self.process_files_worker_instance, files):
        #
        #     self.eventEmit(f)
        #     self.progress()
        #     pools.append(f)
        #     self.copied_files += 1
        #     self.eventEmit("Copied {} of {} ".format(self.copied_files, self.total_files))

        # for f in files :
        #
        #     d = self.p.apply_async(self.process_files_worker_iter ,
        #                           args=f )
        #     self.eventEmit(d)
        #     self.progress()
        #     self.copied_files += 1
        #     self.eventEmit("Copied {} of {} ".format(self.copied_files, self.total_files))

        # for i in files:
        #     self.eventEmit("Processing in file : {} \n".format(i))
        #     process = multiprocessing.Process(target=self.process_files_worker_instance, args=(i,self.resultQueue))
        #     process.start()
        #     self.all_processes.append(process)
        #     self.eventEmit("Copied from {}   \n".format(i ))
        #     self.progress()

        #
        # while True:
        #     event = self.resultQueue.get()
        #     print(event)
        #     if event is None:
        #         break

        # for pro in self.all_processes:
        # #     pro.close()
        #       pro.join()

    def kill_process(self):
        self.eventEmit("terminate pool ")
        for process in self.all_processes:
            process.terminate()
        self.p.terminate()

    @classmethod
    def process_files_worker_queue(cls, files, result):

        str = ""

        while not files.empty():
            ff = files.get()
            print(ff)
            print("\n Left : {} \n".format(files.qsize()))
            base_path, f, destination = ff
            if cls.validate_file_regex(f):
                str += "Processing in {} file : {} \n".format(base_path, f)
                destination_path, source_path = cls.generate_new_file_path(f, base_path, destination)
                print(source_path, destination_path)
                str += cls.copy_files(source_path, destination_path)
                str += "Copied from {}  to {} \n".format(source_path, destination_path)
            else:
                str += "<span style=\" font-size:8pt; font-weight:600; color:red;\" >" + "invalid Name Format. Skipping in " + base_path + " file : " + f + "</span>\n"
                print("Logging from process",str)
            result.put(str)
            return str

    def process_result_worker(self):
        while True:
            res = self.resultQueue.get()
            self.eventEmit(res)
            self.progress()
            is_killed = self.stop_threads.wait()
            if is_killed:
                break
        print("Killing Thread")

    def kill_thread(self):
        print("Thread killing")
        self.stop_threads.set()

    def generate_file_list(self):

        files = [(dire, f, self.destination) for dire in self.input_directory if self.check_exist(dire, "source") for f
                 in listdir(dire)]
        return files

    def generate_json_file(self):
        rootdir = self.destination.rstrip(os.sep)
        for path, dirs, files in os.walk(rootdir):

            if len(files) != 0:
                folders = path.split("/")[-1].split(os.sep)

                self.json_dict[folders[0]][folders[1]][folders[2]][folders[3]][folders[4]].append(
                    [path + f for f in files])

        with open(self.destination +'result.json', 'w') as fp:
            json.dump(self.json_dict, fp)
            url = bytearray(QUrl.fromLocalFile(
                self.destination + "result.json").toEncoded()).decode()
            text = "<a href={}>{}</a>".format(url, url)
            self.json_file_link.emit("JSON MANIFEST FILE: " + text)

    @classmethod
    def generate_new_file_path(cls, f, base_path, destination):
        split__ = f.split("_")
        yyyymmddhhmm = cls.date_from_file(base_path + "/" + f)
        split_dot = split__[2].split(".")

        destination_base_path = destination + split__[0] + "/"

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
        print("srcsize: {}".format(src_size), "dstsize", dst_size)
        try:
            progress_percent = (dst_size / src_size) * 100
        except ZeroDivisionError:
            progress_percent = 100
        self.eventEmit(str(round(progress_percent)) + "% complete")
        self.progress_bar.emit(round(progress_percent))
        if progress_percent == 100:
            self.generate_json_file()
        # self.eventEmit(str(round(progress_percent)) + "% complete")

    @staticmethod
    def copy_files(source_path, destination_path):
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        shutil.copy(source_path, destination_path)
        return "Copying files from {} to {} ".format(source_path, destination_path)

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

#
# if __name__ == "__main__":
#     multiprocessing.freeze_support()
#     fds = FileSyncProcess(["E:/test/source1", "E:/test/source2", "E:/test/source3"], "E:/test/destination")
#     fds.sync()
