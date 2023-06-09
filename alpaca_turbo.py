#!/bin/python3
import json
import logging
import os
import platform
import signal
import sys
from time import sleep, time
import pdb

import psutil
from interact import Process as process
from rich import print as eprint
from rich.logging import RichHandler
from rich.progress import track
import pexpect


class Assistant:
    """Alpaca Assistant"""

    def __init__(self, model_path, context_path, user_type, skip_student_context = 6, skip_tutor_context = 5) -> None:
        self.DEBUG = True
        self.seed = 888777
        self.threads = 4
        self.batch_size = 400
        self.top_k = 40
        self.top_p = 0.9
        self.temp = 0.8
        self.repeat_last_n = 64
        self.repeat_penalty = 1.1
        self.model_path = model_path
        self.context_path = context_path
        self.user_type = user_type
        self.skip_student_context = skip_student_context
        self.skip_tutor_context = skip_tutor_context
        self.prompt = "Tutor:" if user_type == "Student:" else "Student:"

        if platform.system() == "Windows":
            self.model_path = os.path.expanduser(self.model_path).replace(
                "/", "\\"
            )
        else:
            self.model_path = os.path.expanduser(self.model_path)

        self.enable_history = False
        self.is_ready = False

        self.end_marker = b"{self.user_type}"

        self.chat_history = []
        self._killed=False

    def reload(self):
        try:
            self._killed = True
            self.program.kill(signal.SIGTERM)
            sleep(2)
        except:
            pass
        self.is_ready = False
        self.prep_model()

    @staticmethod
    def get_bin_path():
        if os.path.exists("bin/local"):
            return "bin/local"
        system_name = platform.system()
        if system_name == "Linux":
            name = "linux"
        elif system_name == "Windows":
            name = "win.exe"
        elif system_name == "Darwin":
            name = "mac"
        else:
            exit()

        return os.path.join("bin", name)

    @property
    def command(self):
        command = [
            Assistant.get_bin_path(),
            "-t",
            f"{self.threads}",
            "--repeat_penalty",
            f"{self.repeat_penalty}",
            "-m",
            f"{self.model_path}" ,
            "-f",
            f"{self.context_path}",
            "-c",
            "2048",
            "-b",
            "2048",
            "-n",
            "128",
            "--keep",
            "30",
            "-r",
            f"{self.prompt}",
            "--temp",
            f"{self.temp}",
            "--top_p",
            f"{self.top_p}",
            "-i"
        ]
        return command

    def prep_model(self):
        if self.is_ready:
            return None
        _ = (
            ""
            if os.path.exists(self.model_path)
            else print("Set the model path in settings")
        )
        if not os.path.exists(self.model_path):
            return

        tstart = time()
        cmd = self.command
        _ = eprint(cmd)
        file_name = "./pid" + "_" + self.prompt[:-1].lower()
        self.program = process(cmd, timeout=600, maxread=2000, searchwindowsize=None, logfile=None, cwd=None,env=None, encoding=None, codec_errors="strict", preexec_fn=None, file_name=file_name)
        self._killed = False
        self.program.readline()
        self.program.recvuntil(b"...\n")

        # pdb.set_trace()
        model_done = False
        for _ in track(range(32), "Loading Model"):
            self.program.readline()

        
        if self.user_type == 'Student:':
            for _ in track(range(self.skip_student_context), "Loading Model Context for Student"):
                print(self.program.readline())
        else:
            for _ in track(range(self.skip_tutor_context), "Loading Model Context for Teacher"):
                print(self.program.readline())
        # pdb.set_trace()
        self.is_ready = True
        tend = time()
        eprint(f"Model Loaded in {(tend-tstart)} s")

    def streamer(
        self,
        stuff_to_type,
        conv_id
    ):
        if not self.is_ready:
            raise FileNotFoundError(
                f"Cannot locate the specified model : {Assistant.model_path}\n Did you put the correct path in settings=>model_path?\n"
           )

        if conv_id == 0:
           print(self.program.recvuntil(b":"))
    
        self.program.sendline(stuff_to_type)
    
        if self._killed:
            return b""
        print("Waiting...")
        return self.program.recvuntil(self.prompt)
    
    def ask_bot(self, question, conv_id, answer=""):
        print("Started Processing...")
        buffer = self.streamer(question, conv_id)
    
        # Check if buffer contains prompt
        while f"{self.user_type}".encode() not in buffer:
            print("User type not in prompt. Attempting to read next line. Current line: " + buffer.decode("utf-8"))
            
            if f"{self.prompt}".encode() in buffer:
                print("Prompt being asked again, sending empty line")
                self.program.sendline("")
            try:
                buffer = self.program.readline()
            except pexpect.exceptions.TIMEOUT:
                print("Timeout occurred while reading line.")
                break
            
        print("Done.", buffer)
        return buffer.decode("utf-8").strip("\n").strip().replace("Tutor: ", "").replace("Student: ", "").replace("\nStudent:", "").replace("\nTutor:", "").replace("Student:", "").replace("Tutor:", "").replace("\n", "").replace("\end{code}", "")
