import socket
import sys
import time
import argparse

PROXY_HOST = '127.0.0.1'
PROXY_PORT = 8080
UDP_PORT = 9000


def send_tcp_request(path):
    pass # Koneksi ke TCP


def send_udp_request():
    pass # Koneksi ke UDP


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['tcp', 'udp'], default='tcp')
    parser.add_argument('--path', default='/index.html')
    args = parser.parse_args()


if __name__ == '__main__':
    main()
