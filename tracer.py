"""TRACERT"""
import ipaddress
import sys
import re
from socket import socket, AF_INET, SOCK_RAW, IPPROTO_ICMP, \
    IPPROTO_IP, IP_HDRINCL, error, SOCK_DGRAM, create_connection, \
    timeout, gethostbyname, gaierror
from struct import pack
from argparse import ArgumentParser
from logging import warning


DEFAULT_TTL = 30
DEFAULT_WHOIS_SERVER = "whois.iana.org"
WHOIS_PORT = 43
TIMEOUT = 5


def main():
    """ICMP with different ttl packing,
    sending and the answers receiving."""
    destination = argument_parse()

    try:
        sock = socket(AF_INET, SOCK_RAW, IPPROTO_ICMP)
        sock.setsockopt(IPPROTO_IP, IP_HDRINCL, 1)
        sock.settimeout(TIMEOUT)
    except error:
        print("Permission denied")
        sys.exit(0)

    source = get_ip()
    try:
        try:
            address = gethostbyname(destination[0])  # IP - string.
            print(address + ":")
            hope = 1
            current_address = ""
            max_ttl = DEFAULT_TTL
            while hope <= max_ttl and current_address != address:
                buff = package_assembly(hope, source, address)
                sock.sendto(buff, (destination[0], 0))
                try:
                    reply = sock.recvfrom(1024)  # bytes
                    current_address = reply[1][0]
                    print("{}) {}".format(hope, current_address))
                    if is_local_ip(current_address):
                        print("local")
                    country, netname, autonomic_system = get_info(current_address)
                    if country is not None:
                        print("\tCountry: {}".format(country))
                    if netname is not None:
                        print("\tNetname: {}".format(netname))
                    if autonomic_system is not None:
                        print("\tAutonomic system: {}".format(autonomic_system))
                    print()
                except timeout:
                    print("{}) {}".format(hope, "*"))
                    print()
                hope += 1
        except gaierror:
            warning("Wrong destination: {}".format(destination[0]))
    except timeout:
        print("Timeout exceeded.")
    finally:
        sock.close()


def is_local_ip(ip):
    """Checks if the IP address is local."""
    try:
        ip_obj = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return ip_obj.is_private


def argument_parse():
    """Argument parsing."""
    parser = ArgumentParser()
    parser.add_argument("destination", type=str, nargs="*", default="e1.ru")
    args = parser.parse_args()
    return args.destination


def package_assembly(ttl, source, destination):
    """Request package assembling."""
    version_ihl = 4 << 4 | 5
    total_length = 60
    protocol_icmp = 1
    source = address_format(source)
    destination = address_format(destination)
    echo_icmp = 8

    ip_header = pack("!BBHLBBH", version_ihl, 0, total_length,
            0, ttl, protocol_icmp, 0) + source + destination
    icmp_header = pack("!BBHL", echo_icmp, 0, 0, 0)
    icmp_checksum = calc_checksum(icmp_header)
    icmp_header = pack("!BBHL", echo_icmp, 0, icmp_checksum, 0)
    result = ip_header + icmp_header

    return result


def address_format(address):
    """Returns a packed IP-address."""
    addr = tuple(int(x) for x in address.split('.'))
    return pack("!BBBB", addr[0], addr[1], addr[2], addr[3])


def get_ip():
    """
    Request to the external host sending.
    Returns an external IP-address of a current host.
    Source IP-address
    """
    sock = socket(AF_INET, SOCK_DGRAM)
    try:
        sock.connect((DEFAULT_WHOIS_SERVER, WHOIS_PORT))
        return sock.getsockname()[0]
    finally:
        sock.close()


def calc_checksum(packet):
    """Checksum calculate"""
    words = [int.from_bytes(packet[_:_+2], "big") for _ in range(0, len(packet), 2)]
    checksum = sum(words)
    while checksum > 0xffff:
        checksum = (checksum & 0xffff) + (checksum >> 16)
    return 0xffff - checksum


def send_request(request, host_port):
    """Sends a request to host on a port, returns a reply."""
    sock = socket(AF_INET, SOCK_DGRAM)
    sock.settimeout(TIMEOUT)
    sock = create_connection(host_port, TIMEOUT)
    data = bytes()
    try:
        sock.sendall("{}\r\n".format(request).encode('utf-8'))
        while True:
            buff = sock.recv(1024)
            if not buff:
                return data.decode("utf-8")
            data += buff
    finally:
        sock.close()


def get_info(address):
    """Returns country, network name and an autonomic
    system number of a given address"""
    REFER = re.compile(r"refer: (.*?)\n")
    COUNTRY = re.compile(r"country: (.*?)\n")
    NETNAME = re.compile(r"netname: (.*?)\n")
    AUTONOMIC_SYSTEM = re.compile(r"origin: (.*?)\n")
    reply = send_request(address, (DEFAULT_WHOIS_SERVER, WHOIS_PORT))
    refer = re.search(REFER, reply)
    if refer is not None:
        refer = refer.groups()[0].replace(' ', '')
        reply = send_request(address, (refer, WHOIS_PORT))
    for pattern in COUNTRY, NETNAME, AUTONOMIC_SYSTEM:
        match = re.search(pattern, reply)
        if match is not None:
            yield match.groups()[0].replace(' ', '')
        else:
            yield None


if __name__ == "__main__":
    main()
