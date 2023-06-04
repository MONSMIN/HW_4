import json
import logging
import pathlib
import socket
import urllib.parse
import mimetypes
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

from jinja2 import Environment, FileSystemLoader
from threading import Thread

BASE_DIR = pathlib.Path()
env = Environment(loader=FileSystemLoader('templates'))
SERVER_IP = '127.0.0.1'
SERVER_PORT = 5000
BUFFER = 1024

def send_data_to_socket(body):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.sendto(body, (SERVER_IP,SERVER_PORT))
    client_socket.close()


class HTTPHandler(BaseHTTPRequestHandler):


    def do_POST(self):
        body = self.rfile.read(int(self.headers['Content-Length']))
        send_data_to_socket(body)
        self.send_response(302)
        self.send_header('Location', '/message.html')
        self.end_headers()


    def do_GET(self):
        route = urllib.parse.urlparse(self.path)
        match route.path:
            case "/static":
                self.render_template('index.html')
            case "/message.html":
                self.render_template('message.html')
            case _:
                file = BASE_DIR / route.path[1:]
                if file.exists():
                    self.send_static(file)
                else:
                    self.render_template('error.html', 404)


    def render_template(self, filename, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        with open('data.json', 'r', encoding='utf-8') as fd:
            r = json.load(fd)
        template = env.get_template(filename)
        print(template)
        html = template.render(blogs=r)
        self.wfile.write(html.encode())


    def send_html(self, filename, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as f:
            self.wfile.write(f.read())


    def send_static(self, filename):
        self.send_response(200)
        mine_type, *rest = mimetypes.guess_type(filename)

        if mine_type:
            self.send_header('Content-Type', mine_type)
        else:
            self.send_header('Content-Type', 'text/plan')
        self.end_headers()

        with open(filename, 'rb') as f:
            self.wfile.write(f.read())


def run(server=HTTPServer, handler=HTTPHandler):
    address = ('0.0.0.0', 3000)
    http_server = server(address, handler)
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()


def save_data(data):
    body = urllib.parse.unquote_plus(data.decode())
    try:
        payload = {key: value for key, value in [el.split('=') for el in body.split('&')]}

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        new_entry = {timestamp: payload}

        file_path = BASE_DIR.joinpath('storage/data.json')
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as fd:
                try:
                    existing_data = json.load(fd)
                except json.JSONDecodeError:
                    existing_data = {}
        else:
            existing_data = {}

        existing_data.update(new_entry)

        with open(file_path, 'w', encoding='utf-8') as fd:
            json.dump(existing_data, fd, indent=2)

    except ValueError as err:
        logging.error(f"Field parse data: {body} with error {err}")
    except OSError as err:
        logging.error(f"Field write data: {body} with error {err}")


def run_socket_server(ip, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server = ip, port
    server_socket.bind(server)
    try:
        while True:
            data, address = server_socket.recvfrom(BUFFER)
            save_data(data)
    except KeyboardInterrupt:
        logging.info('Socket server stopped')
    finally:
        server_socket.close()



if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format="%(threadName)s %(message)s")
    # STORAGE_DIR = pathlib.Path().joinpath('data')
    # FILE_STORAGE = STORAGE_DIR / 'data.json'
    # if not FILE_STORAGE.exists():
    #     with open(FILE_STORAGE, 'w', encoding='utf-8') as fd:
    #         json.dump({}, fd, ensure_ascii=False)

    thread_server = Thread(target=run)
    thread_server.start()

    thread_socket = Thread(target=run_socket_server(SERVER_IP,SERVER_PORT))
    thread_socket.start()

