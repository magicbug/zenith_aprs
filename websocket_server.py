import asyncio
import json
import websockets
import socket
from loguru import logger
from config import config
from agwpe_handler import AGWPEHandler

class WebSocketServer:
    """Handles WebSocket connections and packet forwarding"""
    
    def __init__(self):
        self.agwpe = AGWPEHandler()
        self.clients = set()
        self.agwpe_connected = False
        self.server = None
        
    async def start(self):
        """Start the WebSocket server and AGWPE connection"""
        try:
            # Connect to AGWPE
            logger.info("Attempting to connect to AGWPE server")
            self.agwpe_connected = await self.agwpe.connect()
            if not self.agwpe_connected:
                logger.warning("AGWPE connection failed, running in WebSocket-only mode")
            else:
                logger.info("AGWPE connection successful")
            
            # Get local IP addresses
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            logger.info(f"Hostname: {hostname}")
            logger.info(f"Local IP: {local_ip}")
            
            # Start WebSocket server
            logger.info(f"Attempting to bind WebSocket server to {config.websocket.host}:{config.websocket.port}")
            
            # Create server with error handling
            try:
                self.server = await websockets.serve(
                    self.handle_client,
                    config.websocket.host,
                    config.websocket.port,
                    reuse_port=True
                )
                logger.info("WebSocket server created successfully")
            except Exception as e:
                logger.error(f"Failed to create WebSocket server: {e}")
                raise
            
            # Log all bound addresses
            if not self.server.sockets:
                logger.error("No sockets bound to server")
                raise RuntimeError("No sockets bound to server")
                
            for sock in self.server.sockets:
                bound_addr = sock.getsockname()
                logger.info(f"Server bound to: {bound_addr}")
                logger.info(f"Server is listening on: ws://{bound_addr[0]}:{bound_addr[1]}")
            
            # Start packet receiver if AGWPE is connected
            if self.agwpe_connected:
                asyncio.create_task(self.receive_packets())
                logger.info("Started AGWPE packet receiver")
            
            # Keep server running
            logger.info("WebSocket server is running")
            await self.server.wait_closed()
            
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            raise
        
    async def handle_client(self, websocket, path):
        """Handle incoming WebSocket connections"""
        client_address = websocket.remote_address
        logger.info(f"New client connecting from {client_address}")
        
        try:
            self.clients.add(websocket)
            logger.info(f"Client connected from {client_address}. Total clients: {len(self.clients)}")
            
            # Send initial connection status
            await websocket.send(json.dumps({
                'status': 'connected',
                'agwpe_connected': self.agwpe_connected
            }))
            
            async for message in websocket:
                try:
                    # Parse incoming message
                    data = json.loads(message)
                    logger.debug(f"Received message from {client_address}: {data}")
                    
                    # Validate required fields
                    if not all(k in data for k in ['to', 'via', 'data']):
                        error_msg = 'Missing required fields: to, via, data'
                        logger.warning(f"{error_msg} from {client_address}")
                        await websocket.send(json.dumps({
                            'error': error_msg
                        }))
                        continue
                        
                    # Send packet through AGWPE if connected
                    if self.agwpe_connected:
                        success = self.agwpe.send_packet(
                            data['to'],
                            data['via'],
                            data['data'].encode()
                        )
                        
                        # Send response
                        response = {
                            'status': 'success' if success else 'error',
                            'message': 'Packet sent' if success else 'Failed to send packet'
                        }
                        logger.debug(f"Sending response to {client_address}: {response}")
                        await websocket.send(json.dumps(response))
                    else:
                        error_msg = 'AGWPE server not connected'
                        logger.warning(error_msg)
                        await websocket.send(json.dumps({
                            'error': error_msg
                        }))
                    
                except json.JSONDecodeError as e:
                    error_msg = 'Invalid JSON format'
                    logger.warning(f"{error_msg} from {client_address}: {e}")
                    await websocket.send(json.dumps({
                        'error': error_msg
                    }))
                except Exception as e:
                    logger.error(f"Error processing message from {client_address}: {e}")
                    await websocket.send(json.dumps({
                        'error': str(e)
                    }))
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client connection closed: {client_address}")
        except Exception as e:
            logger.error(f"Error handling client {client_address}: {e}")
        finally:
            self.clients.remove(websocket)
            logger.info(f"Client disconnected: {client_address}. Total clients: {len(self.clients)}")
            
    async def receive_packets(self):
        """Continuously receive packets from AGWPE and forward to clients"""
        while self.agwpe_connected:
            try:
                packet = self.agwpe.receive_packet()
                if packet:
                    from_callsign, to_callsign, via, data = packet
                    
                    # Create JSON message
                    message = {
                        'from': from_callsign,
                        'to': to_callsign,
                        'via': via,
                        'data': data.decode() if isinstance(data, bytes) else data
                    }
                    
                    # Forward to all connected clients
                    if self.clients:
                        logger.debug(f"Forwarding packet to {len(self.clients)} clients: {message}")
                        await asyncio.gather(*[
                            client.send(json.dumps(message))
                            for client in self.clients
                        ])
                        
            except Exception as e:
                logger.error(f"Error in receive_packets: {e}")
                # If we get an error, try to reconnect to AGWPE
                self.agwpe_connected = await self.agwpe.connect()
                if not self.agwpe_connected:
                    logger.warning("AGWPE reconnection failed, retrying in 5 seconds")
                    await asyncio.sleep(5)
                
            await asyncio.sleep(0.1)  # Prevent CPU hogging 