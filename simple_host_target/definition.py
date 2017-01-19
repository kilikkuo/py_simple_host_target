OP_HT_DATA_BEGIN       = bytearray("HTDTBegin", "ASCII")
OP_HT_DATA_END         = bytearray("HTDTEnd", "ASCII")
OP_SH_DATA_PREFIX       = bytearray("SHDTPre", "ASCII")
OP_SH_DATA_MIDFIX       = bytearray("SHDTMid", "ASCII")
OP_SH_DATA_POSTFIX      = bytearray("SHDTPost", "ASCII")

HOST_PORT   = 7788
TARGET_PORT = 5566

import os
import socket
import pickle
import traceback
import threading
from simple_host_target.client import Client
from simple_host_target.server import Server
from simple_host_target.generaltaskthread import TaskThread, Task

def get_local_IP():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 1))
    ip = s.getsockname()[0]
    s.close()
    return ip

# Exported definitions
class ResultWrapper:
    def __init__(self, token, bytes_result):
        # To identify sender-host-target relationship
        self.token = token

        # A bytesArray which represents the serialized result.
        self.bytes_result = bytes_result

    def get_result(self):
        return self.bytes_result

# Exported definitions
class ExecutorWrapper(object):
    def __init__(self, token, bytes_program, bytes_program_loader):
        # To identify sender-host-target relationship
        self.token = token

        # A bytesArray which represents the serialized program.
        self.bytes_program = bytes_program
        # The loader to help you load the serialized program and
        # execute it !
        self.bytes_program_loader = bytes_program_loader

    def execute(self):
        exec(self.bytes_program_loader)
        data = locals()['bytes_program_loader'](self.bytes_program)
        return data

# TODO : Make token machine specific
token = 0
# TODO : Design a procedure to ensure the termination of this thread
process_thread = None
server = None
def recv_result_from_host(ip_port_pairs, token, callback):
    print("[TempTask] token(%d) going to recv_result_from_host pipeout "%(token))

    ip = ip_port_pairs.get("sender_ip", "")
    port = ip_port_pairs.get("sender_port", "")
    global server
    if server == None:
        server = Server(ip, int(port))
        def data_cb(package):
            pass
        def sh_cb(ip_pairs, package):
            print("SH_CALLBACK = %s"%(str(package)))
            callback(package)
            pass

        server.run_server(data_cb, callback_info = { 1 : { "pre" : OP_SH_DATA_PREFIX,
                                                           "post": OP_SH_DATA_POSTFIX,
                                                           "mid" : OP_SH_DATA_MIDFIX,
                                                           "callback" : sh_cb } })


class SendTask(Task):
    def __init__(self, ip_port_pairs, token, program_bitstream, program_loader_scripts, callback):
        Task.__init__(self)
        self.ip_port_pairs = ip_port_pairs
        self.token = token
        self.wrapper = ExecutorWrapper(token, program_bitstream, program_loader_scripts)
        self.callback = callback

    def run(self):
        print("[SendTask] token(%d) going to dump and open pipein "%(self.token))
        serialized_package = pickle.dumps(self.wrapper)

        host_ip = self.ip_port_pairs.get("host_ip", "")
        host_port = self.ip_port_pairs.get("host_port", HOST_PORT)

        ip_port = repr(self.ip_port_pairs)
        c = Client(ip = host_ip, port = host_port)
        c.send_sh_data(ip_port, serialized_package)

        recv_result_from_host(self.ip_port_pairs, self.token, self.callback)

def send_task_to_host(ip_port_pairs, program_bitstream, program_loader_scripts, callback):
    global process_thread
    global token
    if process_thread == None:
        process_thread = TaskThread(name="task_thread")
        process_thread.start()
    try:
        token += 1
        task = SendTask(ip_port_pairs, token, program_bitstream, program_loader_scripts, callback)
        process_thread.addtask(task)
    except:
        traceback.print_exc()

def sht_proxy_shutdown():
    global server
    if server:
        server.shutdown()
    global process_thread
    if process_thread:
        process_thread.stop()
        process_thread = None
