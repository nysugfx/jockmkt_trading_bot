import os
import sys
from http.server import BaseHTTPRequestHandler

from jinja2 import Environment, FileSystemLoader
from jockmkt_sdk.client import Client

from .controllers.holdings import build_holdings_dict
from .controllers.pnl_calc import pnl_calc

file_loader = FileSystemLoader('jockbot/templates')
env = Environment(loader=file_loader)


routes = {
    "/": "Hello World",
    "/health": "Success",
}

class HiddenPrints:
    def __enter__(self):
        self._original_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stdout = self._original_stdout

class Server(BaseHTTPRequestHandler):
    def __init__(self, client: Client, event_id: str, *args, **kwargs):
        self.client: Client = client
        self.event_id: str = event_id
        super().__init__(*args, **kwargs)

    def do_GET(self):
        self.respond()

    def do_HEAD(self):
        return

    def do_POST(self):
        return

    def handle_http(self, status, content_type):
        if self.path == '/pnl':
            with HiddenPrints():
                content = pnl_calc(self.client, self.event_id)
            template = env.get_template('pnl.html')
            output = template.render(content=content)
        elif self.path == '/holdings':
            with HiddenPrints():
                content = build_holdings_dict(self.client, self.event_id)
            template = env.get_template('holdings.html')
            output = template.render(content=content)
        elif self.path in routes:
            output = routes[self.path]
        else:
            status = 404
            output = '404: Not Found'
        self.send_response(status)
        self.send_header("Content-type", content_type)
        self.end_headers()
        return bytes(output, "UTF-8")

    def respond(self):
        content = self.handle_http(200, "text/html")
        if content is not None:
            self.wfile.write(content)
