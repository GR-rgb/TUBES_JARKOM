import socket
import threading
import os
import mimetypes
from datetime import datetime

#  CONFIGURASI SERVER
TCP_HOST = "0.0.0.0"
TCP_PORT = 8000

UDP_HOST = "0.0.0.0"
UDP_PORT = 9000

# Path dasar untuk file yang dilayani (misal: index.html, css/, js/)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# helper untuk logging dengan timestamp
def log(tag, message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{tag}] {message}")

# helper untuk membaca file sebagai bytes
def read_file(filepath):
    try:
        with open(filepath, "rb") as f:
            return f.read()
    except FileNotFoundError:
        return None
    except Exception as e:
        log("ERROR", f"Gagal membaca file {filepath}: {e}")
        return None

# helper untuk menyusun HTTP response
def build_response(status_code, status_text, content_type, body_bytes):
    header = (
        f"HTTP/1.1 {status_code} {status_text}\r\n"
        f"Content-Type: {content_type}; charset=utf-8\r\n"
        f"Content-Length: {len(body_bytes)}\r\n"
        f"Connection: close\r\n"
        f"\r\n"
    )
    return header.encode("utf-8") + body_bytes

# helper untuk parsing HTTP request
def parse_request(raw_data):
    try:
        text = raw_data.decode("utf-8", errors="ignore")
        first_line = text.split("\r\n")[0]
        parts = first_line.split(" ")
        if len(parts) < 2:
            return None, None
        method = parts[0]
        path   = parts[1]
        return method, path
    except Exception:
        return None, None

# helper untuk memetakan URL path ke file system path
def resolve_path(url_path):
    # Hapus query string kalau ada
    url_path = url_path.split("?")[0]

    # Path root → index.html
    if url_path == "/":
        url_path = "/index.html"

    # Cegah path traversal (../)
    safe_path = os.path.normpath(url_path.lstrip("/"))
    full_path = os.path.join(BASE_DIR, safe_path)

    return full_path

# handler untuk setiap koneksi TCP masuk
def handle_tcp_client(conn, addr):
    client_ip   = addr[0]
    client_port = addr[1]
    log("TCP", f"Koneksi masuk dari {client_ip}:{client_port}")

    try:
        # Terima request (max 8 KB untuk header)
        raw_data = b""
        conn.settimeout(5)
        try:
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                raw_data += chunk
                # Berhenti setelah menerima header lengkap
                if b"\r\n\r\n" in raw_data:
                    break
        except socket.timeout:
            pass

        if not raw_data:
            log("TCP", f"Request kosong dari {client_ip}")
            return

        method, path = parse_request(raw_data)

        # Request tidak valid
        if method is None:
            response = build_response(400, "Bad Request",
                                      "text/html",
                                      b"<h1>400 Bad Request</h1>")
            conn.sendall(response)
            log("TCP", f"{client_ip} → 400 Bad Request (malformed)")
            return

        log("TCP", f"{client_ip} → {method} {path}")

        # Hanya tangani GET
        if method != "GET":
            response = build_response(405, "Method Not Allowed",
                                      "text/html",
                                      b"<h1>405 Method Not Allowed</h1>")
            conn.sendall(response)
            log("TCP", f"{client_ip} → 405 Method Not Allowed")
            return

        # ── Resolve path ──────────────────────────────────────
        full_path = resolve_path(path)

        # Tentukan content-type berdasarkan ekstensi
        mime_type, _ = mimetypes.guess_type(full_path)
        if mime_type is None:
            mime_type = "application/octet-stream"

        # ── Baca file ─────────────────────────────────────────
        body = read_file(full_path)

        if body is not None:
            # 200 OK
            response = build_response(200, "OK", mime_type, body)
            conn.sendall(response)
            log("TCP", f"{client_ip} → 200 OK | {path} ({len(body)} bytes)")

        else:
            # 404 Not Found → kirim halaman 404 kustom
            error_path = os.path.join(BASE_DIR, "status", "404.html")
            error_body = read_file(error_path)
            if error_body is None:
                error_body = b"<h1>404 Not Found</h1>"
            response = build_response(404, "Not Found", "text/html", error_body)
            conn.sendall(response)
            log("TCP", f"{client_ip} → 404 Not Found | {path}")

    except Exception as e:
        # 500 Internal Server Error
        log("ERROR", f"Exception saat handle {client_ip}: {e}")
        try:
            error_path = os.path.join(BASE_DIR, "status", "500.html")
            error_body = read_file(error_path)
            if error_body is None:
                error_body = b"<h1>500 Internal Server Error</h1>"
            response = build_response(500, "Internal Server Error",
                                      "text/html", error_body)
            conn.sendall(response)
            log("TCP", f"{client_ip} → 500 Internal Server Error")
        except Exception:
            pass

    finally:
        conn.close()
        log("TCP", f"Koneksi ditutup: {client_ip}:{client_port}")

# start TCP server untuk HTTP
def start_tcp_server():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((TCP_HOST, TCP_PORT))
    server_sock.listen(10)
    log("TCP", f"Web Server berjalan di port {TCP_PORT} (HTTP)")
    log("TCP", f"Base directory: {BASE_DIR}")

    while True:
        try:
            conn, addr = server_sock.accept()
            # Spawn thread baru untuk setiap koneksi masuk
            t = threading.Thread(target=handle_tcp_client, args=(conn, addr), daemon=True)
            t.start()
            log("TCP", f"Thread baru dibuat untuk {addr[0]}:{addr[1]} "
                       f"(aktif: {threading.active_count() - 2})")  # -2: main + udp thread
        except KeyboardInterrupt:
            log("TCP", "Server dihentikan.")
            break
        except Exception as e:
            log("ERROR", f"Error accept: {e}")

    server_sock.close()

# start UDP server untuk QoS (echo server sederhana)
def start_udp_server():
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind((UDP_HOST, UDP_PORT))
    log("UDP", f"UDP Echo Server berjalan di port {UDP_PORT} (QoS)")

    while True:
        try:
            # Terima paket UDP
            data, addr = udp_sock.recvfrom(1024)
            client_ip = addr[0]

            # Echo balik payload tanpa modifikasi
            udp_sock.sendto(data, addr)
            log("UDP", f"Echo ke {client_ip} | payload: {data.decode('utf-8', errors='ignore').strip()}")

        except KeyboardInterrupt:
            log("UDP", "UDP Server dihentikan.")
            break
        except Exception as e:
            log("ERROR", f"UDP error: {e}")

    udp_sock.close()

# main function untuk menjalankan server
def main():
    log("MAIN", "=" * 50)
    log("MAIN", " IFLAB Web Server - Tubes Jaringan Komputer")
    log("MAIN", "=" * 50)

    # Jalankan UDP server di thread terpisah (daemon)
    udp_thread = threading.Thread(target=start_udp_server, daemon=True)
    udp_thread.start()

    # Jalankan TCP server di main thread
    try:
        start_tcp_server()
    except KeyboardInterrupt:
        log("MAIN", "Server dimatikan dengan Ctrl+C.")


if __name__ == "__main__":
    main()