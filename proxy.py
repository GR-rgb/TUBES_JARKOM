import socket
import threading
import sys
import time

HOST = '0.0.0.0'
PROXY_PORT = 8080
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 8000

cache = {}
cache_lock = threading.Lock()


def handle_client(conn, addr):
    pass # Terima requet dari client


def start_proxy():
    pass # Setup proxy server


def main():
    pass


if __name__ == '__main__':
    main()
