from pydantic import BaseModel, Field
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class AGWPEConfig(BaseModel):
    """AGWPE TCP connection configuration"""
    host: str = Field(default="127.0.0.1", description="AGWPE server host")
    port: int = Field(default=8000, description="AGWPE server port")
    callsign: str = Field(..., description="Your amateur radio callsign")
    ssid: int = Field(default=0, description="SSID for your callsign")

class WebSocketConfig(BaseModel):
    """WebSocket server configuration"""
    host: str = Field(default="0.0.0.0", description="WebSocket server host")
    port: int = Field(default=8765, description="WebSocket server port")

class Config(BaseModel):
    """Main application configuration"""
    agwpe: AGWPEConfig
    websocket: WebSocketConfig
    debug: bool = Field(default=False, description="Enable debug logging")

# Load configuration from environment variables
config = Config(
    agwpe=AGWPEConfig(
        host=os.getenv("AGWPE_HOST", "127.0.0.1"),
        port=int(os.getenv("AGWPE_PORT", "8000")),
        callsign=os.getenv("CALLSIGN", ""),
        ssid=int(os.getenv("SSID", "0"))
    ),
    websocket=WebSocketConfig(
        host=os.getenv("WS_HOST", "0.0.0.0"),
        port=int(os.getenv("WS_PORT", "8765"))
    ),
    debug=os.getenv("DEBUG", "false").lower() == "true"
) 