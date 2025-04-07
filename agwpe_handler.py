import asyncio
from loguru import logger
from pe import PacketEngine, ReceiveHandler, app
from config import config
from queue import Queue

class AGWPEReceiveHandler(ReceiveHandler):
    """Custom receive handler for AGWPE frames"""
    def __init__(self):
        super().__init__()
        self.frame_queue = Queue()
        
    def monitored_unproto(self, port, call_from, call_to, text, data):
        """Handle received unproto frames"""
        logger.debug(f"Received unproto frame: {call_from} -> {call_to} via {text}")
        logger.debug(f"Frame data: {data}")
        self.frame_queue.put((call_from, call_to, text, data))
        
    def monitored_connected(self, port, call_from, call_to, text, data):
        """Handle received connected frames"""
        logger.debug(f"Received connected frame: {call_from} -> {call_to} via {text}")
        logger.debug(f"Frame data: {data}")
        self.frame_queue.put((call_from, call_to, text, data))
        
    def monitored_supervisory(self, port, call_from, call_to, text):
        """Handle received supervisory frames"""
        logger.debug(f"Received supervisory frame: {call_from} -> {call_to} via {text}")
        self.frame_queue.put((call_from, call_to, text, b""))
        
    def monitored_raw(self, port, data):
        """Handle raw AX.25 frames"""
        logger.debug(f"Received raw frame on port {port}")
        try:
            logger.debug(f"Raw frame data: {data.hex()}")
            self.frame_queue.put(("RAW", "RAW", "", data))
        except Exception as e:
            logger.error(f"Error processing raw frame: {e}")
            
    def monitored_own(self, port, call_from, call_to, pid, data):
        """Handle frames sent by this client"""
        logger.debug(f"Received own frame: {call_from} -> {call_to} pid={pid}")
        logger.debug(f"Frame data: {data}")
        self.frame_queue.put((call_from, call_to, "", data))

class AGWPEHandler:
    """Handles communication with AGWPE server"""
    
    def __init__(self):
        """Initialize AGWPE handler"""
        self.host = config.agwpe.host
        self.port = config.agwpe.port
        self.connected = False
        
        # Create receive handler
        self.receive_handler = AGWPEReceiveHandler()
        
        # Create application instance with our receive handler
        self.app = app.Application()
        self.app.use_custom_handler(self.receive_handler)
        
    async def connect(self):
        """Connect to AGWPE server"""
        try:
            logger.info(f"Connecting to AGWPE server at {self.host}:{self.port}")
            
            # Start the application and connect to server
            self.app.start(self.host, self.port)
            
            # Wait for connection to be established
            await asyncio.sleep(1)
            
            # Check if we're connected by attempting to get version info
            try:
                self.app.engine.ask_version()
                
                # Enable monitoring to receive packets
                self.app.enable_monitoring = True
                # Enable raw AX.25 frame reception
                self.app.engine.raw_ax25 = True
                # Enable monitoring of own packets
                self.app.engine.monitor_own = True
                logger.info("Enabled packet monitoring, raw AX.25 frames, and own packet monitoring")
                
                self.connected = True
                logger.info("Successfully connected to AGWPE server")
                return True
            except Exception as e:
                logger.error("Failed to establish connection")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to AGWPE server: {e}")
            self.connected = False
            return False
            
    def disconnect(self):
        """Disconnect from AGWPE server"""
        if self.connected:
            try:
                self.app.stop()
                logger.info("Disconnected from AGWPE server")
            except Exception as e:
                logger.error(f"Error disconnecting from AGWPE server: {e}")
        self.connected = False
        
    def send_packet(self, to_callsign, via, data):
        """Send packet through AGWPE"""
        if not self.connected:
            logger.warning("Cannot send packet: Not connected to AGWPE server")
            return False
            
        try:
            # Convert string data to bytes if needed
            if isinstance(data, str):
                data = data.encode()
                
            # Handle VIA path - ensure it's a list of strings
            via_path = []
            if via:
                # Split on commas if multiple paths, otherwise use as single path
                if ',' in via:
                    via_path = [path.strip() for path in via.split(',')]
                else:
                    via_path = [via.strip()]
                
            # Send unproto frame
            self.app.send_unproto(
                port=0,
                call_from=f"{config.agwpe.callsign}-{config.agwpe.ssid}",
                call_to=to_callsign,
                data=data,
                via=via_path if via_path else None
            )
            
            logger.debug(f"Sent packet to {to_callsign} via {via_path} with {len(data)} bytes")
            return True
            
        except Exception as e:
            logger.error(f"Error sending packet: {e}")
            return False
            
    def receive_packet(self):
        """Receive a packet from AGWPE"""
        if not self.connected:
            return None
            
        try:
            # Try to get a frame from the queue with 1 second timeout
            try:
                frame = self.receive_handler.frame_queue.get(timeout=1.0)
                if frame:
                    # Convert data to string if it's bytes or bytearray
                    call_from, call_to, via, data = frame
                    if isinstance(data, (bytes, bytearray)):
                        try:
                            data = data.decode('utf-8')
                        except UnicodeDecodeError:
                            data = data.hex()  # Fallback to hex if not valid UTF-8
                    return (call_from, call_to, via, data)
                return None
            except:
                return None
            
        except Exception as e:
            if not isinstance(e, TimeoutError):  # Don't log timeout errors
                logger.error(f"Error receiving packet: {e}")
            return None 