import os
import sys
import time
import pickle
import traceback

PACKAGE_PARENT = '..'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))
from simple_host_target.client import Client
from simple_host_target.server import Server
from simple_host_target.definition import HOST_PORT, TARGET_PORT,\
                        get_local_IP, OP_SH_DATA_PREFIX,\
                        OP_SH_DATA_POSTFIX, OP_SH_DATA_MIDFIX

class ExecutionHost(object):
    def __init__(self, IP):
        self.host_IP = IP
        self.target_IPs = set()
        self.dicTokenIP = {}
        self.dicToken2Pairs = {}

    def setup_target_IPs(self, target_IPs):
        assert(type(target_IPs) == list and len(target_IPs) > 0), "Must be a list and size > 0."
        self.target_IPs = set(target_IPs)

    def __ensure_target_IPs(self):
        if len(self.target_IPs) == 0:
            print("Empty target IPs, you should call setup_target_IPs before run !!")
            print("Or enter at least a valid Target IP ...")
            try:
                target_IP = ""
                for line in sys.stdin:
                    target_IP = line.strip()
                    break
                self.target_IPs.add(target_IP)
            except:
                print("Something wrong while processing target IP, exit !")
                sys.exit(1)

    def run(self):
        self.__ensure_target_IPs()
        self.server = Server(ip = self.host_IP, port = HOST_PORT)
        self.server.run_server(self.__recv_from_target,
                               callback_info = { 1 : { "pre"   : OP_SH_DATA_PREFIX,
                                                       "post"  : OP_SH_DATA_POSTFIX,
                                                       "mid"   : OP_SH_DATA_MIDFIX,
                                                       "callback" : self.__recv_from_sender
                                                     }
                                               })

        print("Host is running ...")
        while 1:
            try:
                time.sleep(1)
            except:
                traceback.print_exc()
                break
        self.__shutdown()

    def __shutdown(self):
        print("[Host] shutdown ... begin")
        if self.server:
            self.server.shutdown()
            self.server = None
        print("[Host] shutdown ... end")

    def __send_result_to_proxy(self, sh_ip_pairs, serialized_result_wrapper):
        print("result to proxy: %s"%(serialized_result_wrapper))
        sender_ip = sh_ip_pairs.get("sender_ip", "")
        sender_port = sh_ip_pairs.get("sender_port", 0)

        c = Client(ip = sender_ip, port = sender_port)
        c.send_sh_data("", serialized_result_wrapper)
        c.shutdown()

    def __recv_from_sender(self, ip_port_pairs, serialized_executor_wrapper):
        dict_IP_pairs = eval(ip_port_pairs.decode("ASCII"))
        self.__send_execution_task(dict_IP_pairs, serialized_executor_wrapper)

    def __recv_from_target(self, serialized_result_wrapper):
        print("[Host] get result : %s "%(str(serialized_result_wrapper)))
        rw = pickle.loads(serialized_result_wrapper)
        sh_ip_pairs = self.dicToken2Pairs.pop(rw.token, "")
        t_ip = self.dicTokenIP.pop(rw.token, None)
        if t_ip:
            self.target_IPs.add(t_ip)
        self.__send_result_to_proxy(sh_ip_pairs, serialized_result_wrapper)
        pass

    def __send_execution_task(self, ip_port_pairs, serialized_executor_wrapper):
        # TODO : Select one of Target to send task
        t_ip = self.target_IPs.pop() if len(self.target_IPs) else None
        if t_ip == None:
            print("No available target for new job. Try later !!")
            return
        c = None
        try:
            ew = pickle.loads(serialized_executor_wrapper)
            c = Client(ip = t_ip, port = TARGET_PORT)
            c.send_ht_data(serialized_executor_wrapper)
            self.dicTokenIP[ew.token] = t_ip
            self.dicToken2Pairs[ew.token] = ip_port_pairs
        except:
            traceback.print_exc()
            print("[Host][Exception] while sending execution task !")
        finally:
            if c:
                c.shutdown()

def create_host():
    host_ip = get_local_IP()
    print("Creating host @(%s) ... are you sure ? Enter Yes/No."%(host_ip))
    try:
        for line in sys.stdin:
            msg = line.lower()
            if msg.find('yes') >= 0:
                host = ExecutionHost(host_ip)
                return host
            else:
                break
    except:
        traceback.print_exc()
    print("\r\nNothing created")
    return None

if __name__ == "__main__":
    host = create_host()
    if host:
        host.run()
