import threading
import signal
import sys
import time
import asyncio
import traceback
from loguru import logger
from websocket_server import WebSocketServer

# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG"
)
logger.add("aprs_gateway.log", rotation="1 day", level="INFO")

class APRSGateway:
    """Main APRS Gateway application"""
    
    def __init__(self):
        self.websocket_server = WebSocketServer()
        self.running = False
        self.loop = None
        
    def start_websocket_server(self):
        """Start the WebSocket server in its own event loop"""
        try:
            logger.info("Creating new event loop for WebSocket server")
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            logger.info("Starting WebSocket server")
            self.loop.run_until_complete(self.websocket_server.start())
        except Exception as e:
            logger.error(f"Error in WebSocket server: {e}")
            logger.error(traceback.format_exc())
            self.running = False
        
    def start(self):
        """Start the APRS Gateway"""
        self.running = True
        logger.info("Starting APRS Gateway...")
        
        # Handle graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
            
        try:
            # Start WebSocket server in a separate thread
            logger.info("Creating WebSocket server thread")
            ws_thread = threading.Thread(target=self.start_websocket_server)
            ws_thread.daemon = True
            ws_thread.start()
            
            # Keep main thread alive
            logger.info("Main thread running")
            while self.running:
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"Error in APRS Gateway: {e}")
            logger.error(traceback.format_exc())
            self.stop()
            
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}")
        self.stop()
            
    def stop(self):
        """Stop the APRS Gateway"""
        if not self.running:
            return
            
        logger.info("Stopping APRS Gateway...")
        self.running = False
        
        # Cleanup
        if self.websocket_server.agwpe_connected:
            self.websocket_server.agwpe.disconnect()
            
        # Stop the event loop if it exists
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        
        # Exit
        sys.exit(0)

def main():
    """Main entry point"""
    try:
        gateway = APRSGateway()
        gateway.start()
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main() 