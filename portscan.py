import socket
import sys
import threading
import time
from collections import OrderedDict
import struct
import re
from random import randint
from multiprocessing import Pool
import argparse
from multiprocessing import TimeoutError
from _socket import timeout

ID = randint(1, 65535)
DNSPACK = struct.pack("!HHHHHH", ID, 256, 1, 0, 0, 0) + b"\x06google\x03com\x00\x00\x01\x00\x01"
TCP_PACKS = OrderedDict([
    ("dns", struct.pack("!H", len(DNSPACK)) + DNSPACK),
    ("smtp", b'HELO World'),
    ("http", b'GET / HTTP/1.1\r\nHost: google.com\r\n\r\n'),
    ("pop3", b"AUTH")
])
UDP_PACKS = OrderedDict([
    ("dns", DNSPACK),
    ("ntp", struct.pack('!BBBb11I', (2 << 3) | 3, *([0] * 14)))
])


def check_pack(pack):
    """Check packet"""
    if pack[:4].startswith(b"HTTP"):
        return 'http'
    elif re.match(b"[0-9]{3}", pack[:3]):
        return "smtp"
    if struct.pack("!H", ID) in pack:
        return "dns"
    elif pack.startswith(b"+"):
        return "pop3"
    else:
        try:
            struct.unpack('!BBBb11I', pack)
        except:
            return "..."
        else:
            return "ntp"


def is_port_in_use_tcp(addr):
    """Is port in use tcp"""
    ip, port = addr
    socket.setdefaulttimeout(1)
    for prot in TCP_PACKS:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.connect(addr)
                sock.sendall(TCP_PACKS[prot])
                data = sock.recv(12)
                return port, check_pack(data)
            except:
                continue


def is_port_in_use_udp(addr):
    """Is port in use udp"""
    ip, port = addr
    res = "..."
    socket.setdefaulttimeout(1)
    for prot in UDP_PACKS:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            try:
                sock.sendto(UDP_PACKS[prot], addr)
                data, _ = sock.recvfrom(48)
                res = check_pack(data)
            except timeout:
                continue
    if res != "...":
        return port, res


class PortScannerAsync:
    """Async scan of ports class"""

    def __init__(self, ip, udp=False, tcp=False):
        self.addr = ip
        self.pool = Pool()
        self.udp = udp
        self.tcp = tcp

    def start(self, start=1, end=65535):
        time.sleep(2)
        rng = [(self.addr, i) for i in range(start, end)]
        if self.udp:
            func = is_port_in_use_udp
        else:
            func = is_port_in_use_tcp
        sys.stdout.flush()
        return self.pool.imap(func, rng)


def create_parser():
    parser = argparse.ArgumentParser(prog="portscan",
                                     description="Scan of ports of remote host")
    parser.add_argument('-t', default=False, help="scan TCP", action='store_true')
    parser.add_argument('-u', default=False, help="scan UDP", action='store_true')
    parser.add_argument("ip", help="host for scan")
    # --ports
    parser.add_argument("start", type=int, help="range start")
    parser.add_argument("end", type=int, help="range end")
    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()
    if args.t and args.u:
        threads = [threading.Thread(target=print_result, args=(args, False, True, "TCP",)),
                   threading.Thread(target=print_result, args=(args, True, False, "UDP",))]
        for thread in threads:
            thread.start()
    elif args.t:
        print_result(args, False, True, "TCP")
    elif args.u:
        print_result(args, True, False, "UDP")


def print_result(args, udp=False, tcp=False, string=''):
    res = PortScannerAsync(args.ip, udp, tcp).start(args.start, args.end)
    while True:
        try:
            nxt = res.next(timeout=6)
            if nxt:
                print("Port {} {} {}".format(*nxt, string))
        except TimeoutError:
            break
        except StopIteration:
            break


if __name__ == "__main__":
    main()
