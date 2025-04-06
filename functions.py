import json
import asyncio
import websockets
from datetime import datetime
from python_socks.async_.asyncio import Proxy
from python_socks._errors import ProxyError, ProxyTimeoutError, ProxyConnectionError
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.layout import Layout
from rich import box
import time

console = Console()

class ProxyConnectionException(Exception):
    pass

class FarmingUI:
    def __init__(self):
        self.start_time = time.time()
        self.connection_log = []
        self.response_log = []
        self.max_log_lines = 30
        self.total_traffic = 0
    
    def get_uptime(self):
        uptime = int(time.time() - self.start_time)
        hours = uptime // 3600
        minutes = (uptime % 3600) // 60
        seconds = uptime % 60
        return f"{hours:02d}h {minutes:02d}m {seconds:02d}s"
    
    def add_connection_log(self, message, color="white"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_text = Text()
        
        log_text.append("• [", style="#cccccc")
        log_text.append(timestamp, style="#cccccc")
        log_text.append("] ", style="#cccccc")
        
        if '[Acc.' in message:
            acc_part = message.split(']')[0] + ']'
            rest = message.split(']', 1)[1] if ']' in message else message
            log_text.append(acc_part, style="#ffff85")
            log_text.append(rest, style=color)
        else:
            log_text.append(message, style=color)
        
        self.connection_log.append(log_text)
        if len(self.connection_log) > self.max_log_lines:
            self.connection_log.pop(0)
    
    def add_response_log(self, message, color="white"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_text = Text()
        
        log_text.append("• [", style="#cccccc")
        log_text.append(timestamp, style="#cccccc")
        log_text.append("] ", style="#cccccc")
        
        if '[Acc.' in message:
            acc_part = message.split(']')[0] + ']'
            rest = message.split(']', 1)[1] if ']' in message else message
            log_text.append(acc_part, style="#ffff85")
            log_text.append(rest, style=color)
        else:
            log_text.append(message, style=color)
        
        self.response_log.append(log_text)
        if len(self.response_log) > self.max_log_lines:
            self.response_log.pop(0)
    
    def update_traffic(self, bytes_count):
        self.total_traffic += bytes_count

    def format_traffic(self):
        if self.total_traffic < 1024:
            return f"{self.total_traffic}B"
        elif self.total_traffic < 1024 * 1024:
            return f"{self.total_traffic / 1024:.1f}kB"
        else:
            return f"{self.total_traffic / (1024 * 1024):.3f}mB"

    def make_layout(self):
        layout = Layout()
        
        uptime = self.get_uptime()
        uptime_text = Text(f"Uptime: {uptime}", style="bold green")
        traffic_text = Text(f"Traffic: {self.format_traffic()}", style="bold yellow")  # Добавлено
        header_text = Text("Teneo PRO Farming Console", style="bold blue")
        
        spaces = " " * (console.width - len(header_text.plain) - len(uptime_text.plain) - len(traffic_text.plain) - 6)
        header_content = Text.assemble(
            header_text,
            spaces,
            uptime_text,
            " ",
            traffic_text
        )
        header = Panel(header_content, border_style="blue")
        
        connection_panel = Panel(
            Text("\n").join(self.connection_log[-self.max_log_lines:]),
            title="[bold]Connection Log[/]",
            border_style="blue",
            box=box.ROUNDED
        )
        
        response_panel = Panel(
            Text("\n").join(self.response_log[-self.max_log_lines:]),
            title="[bold]Server Responses[/]",
            border_style="blue",
            box=box.ROUNDED
        )
        
        layout.split_column(
            Layout(header, name="header", size=3),
            Layout(name="main")
        )
        
        total_width = console.width
        connections_width = int(total_width * 0.4)
        responses_width = total_width - connections_width
        
        layout["main"].split_row(
            Layout(connection_panel, name="connections", size=connections_width),
            Layout(response_panel, name="responses", size=responses_width)
        )
        
        return layout

class AccountWorker:
    def __init__(self, account_data, ui):
        self.account_id = account_data['account_id']
        self.access_token = account_data['access_token']
        self.proxy = account_data.get('proxy', '')
        self.ws_url = f"wss://secure.ws.teneo.pro/websocket?accessToken={self.access_token}&version=v0.2"
        self.ui = ui
        self.bytes_sent = 0
        self.bytes_received = 0
        
    async def _parse_proxy(self):
        if not self.proxy:
            return None
            
        try:
            proxy_parts = self.proxy.split('@')
            if len(proxy_parts) == 2:
                auth, hostport = proxy_parts
                username, password = auth.split(':')
            else:
                hostport = proxy_parts[0]
                username = password = None
                
            host, port = hostport.split(':')
            return host, int(port), username, password
        except Exception as e:
            raise ProxyConnectionException(f"Invalid proxy format: {str(e)}")

    async def connect(self):
        try:
            if self.proxy:
                proxy_data = await self._parse_proxy()
                if not proxy_data:
                    return await websockets.connect(self.ws_url)
                
                host, port, username, password = proxy_data
                self.ui.add_connection_log(
                    f"[Acc. {self.account_id}] Connecting via proxy {host}:{port}", 
                    "magenta"
                )
                
                proxy = Proxy.from_url(f"socks5://{username}:{password}@{host}:{port}" if username else f"socks5://{host}:{port}")
                sock = await proxy.connect(dest_host='secure.ws.teneo.pro', dest_port=443)
                
                ws = await websockets.connect(
                    self.ws_url,
                    sock=sock,
                    ssl=True,
                    ping_interval=None,
                    close_timeout=2
                )
                
                self.ui.add_connection_log(
                    f"[Acc. {self.account_id}] Connection established", 
                    "green"
                )
                return ws
                
            self.ui.add_connection_log(
                f"[Acc. {self.account_id}] Direct connection", 
                "cyan"
            )
            return await websockets.connect(self.ws_url)
            
        except ProxyConnectionError as e:
            raise ProxyConnectionException(f"Proxy connection error: {str(e)}")
        except ProxyTimeoutError as e:
            raise ProxyConnectionException(f"Proxy timeout: {str(e)}")
        except ProxyError as e:
            raise ProxyConnectionException(f"Proxy error: {str(e)}")
        except Exception as e:
            raise ProxyConnectionException(f"Connection error: {str(e)}")
    
    async def send_pings(self, websocket):
        while True:
            try:
                data = json.dumps({"type": "PING"})
                if self.proxy:
                    bytes_count = len(data.encode('utf-8'))
                    self.bytes_sent += bytes_count
                    self.ui.update_traffic(bytes_count)
                await websocket.send(data)
                self.ui.add_connection_log(
                    f"[Acc. {self.account_id}] Ping", 
                    "light_gray"
                )
                await asyncio.sleep(10)
            except Exception as e:
                self.ui.add_connection_log(
                    f"[Acc. {self.account_id}] Ping error: {str(e)}", 
                    "red"
                )
                raise

    async def listen_responses(self, websocket):
        while True:
            try:
                message = await websocket.recv()
                if self.proxy:
                    bytes_count = len(message)
                    self.bytes_received += bytes_count
                    self.ui.update_traffic(bytes_count)
                self._print_response(message)
            except websockets.exceptions.ConnectionClosed as e:
                self.ui.add_connection_log(
                    f"[Acc. {self.account_id}] Connection closed (code: {e.code})", 
                    "yellow"
                )
                raise
            except Exception as e:
                self.ui.add_connection_log(
                    f"[Acc. {self.account_id}] Receive error: {str(e)}", 
                    "red"
                )
                raise
    
    def _print_response(self, message):
        try:
            data = json.loads(message)
            if data.get("message") == "Pulse from server":
                self.ui.add_response_log(
                    f"[Acc. {self.account_id}] [Pulse] Today: {data['pointsToday']} "
                    f"Total: {data['pointsTotal']} HB: {data['heartbeats']}",
                    "cyan"
                )
                return
            elif data.get("message") == "Connected successfully":
                self.ui.add_response_log(
                    f"[Acc. {self.account_id}] [Connected] Today: {data['pointsToday']} "
                    f"Total: {data['pointsTotal']}",
                    "green"
                )
                return
        except json.JSONDecodeError:
            pass
        self.ui.add_response_log(
            f"[Acc. {self.account_id}] RAW: {message[:100]}{'...' if len(message) > 100 else ''}", 
            "light_gray"
        )

async def process_account(account_data, ui):
    worker = AccountWorker(account_data, ui)
    retries = 5
    
    while retries > 0:
        try:
            async with await worker.connect() as ws:
                retries = 5
                try:
                    await asyncio.gather(
                        worker.send_pings(ws),
                        worker.listen_responses(ws)
                    )
                except asyncio.CancelledError:
                    await ws.close(code=1000, reason='KeyboardInterrupt')
                    raise
                
        except ProxyConnectionException as e:
            retries -= 1
            ui.add_connection_log(
                f"[Acc. {worker.account_id}] Proxy error ({5-retries}/5): {e}", 
                "red"
            )
            if retries > 0:
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            ui.add_connection_log(
                f"[Acc. {worker.account_id}] Graceful shutdown", 
                "yellow"
            )
            return
        except Exception as e:
            retries -= 1
            ui.add_connection_log(
                f"[Acc. {worker.account_id}] Error ({5-retries}/5): {str(e)}", 
                "red"
            )
            if retries > 0:
                await asyncio.sleep(5)