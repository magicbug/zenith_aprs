# APRS Gateway

A Python-based APRS gateway that connects to an AGWPE server and provides a WebSocket interface for sending and receiving APRS packets.

## Features

- Connects to AGWPE server using pyham-pe library
- WebSocket interface for sending and receiving APRS packets
- Supports position reports and text messages
- Real-time packet monitoring and forwarding

## Requirements

- Python 3.8 or higher
- AGWPE server running and accessible
- WebSocket client (test.html provided)

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Create a `.env` file with the following settings:

```env
AGWPE_HOST=localhost
AGWPE_PORT=8000
AGWPE_CALLSIGN=YOURCALL
AGWPE_SSID=0
WEBSOCKET_HOST=localhost
WEBSOCKET_PORT=8765
```

## Usage

1. Start the server:
   ```bash
   python main.py
   ```

2. Open test.html in a web browser to send and receive APRS packets

## WebSocket Interface

The WebSocket server provides the following functionality:

- Send APRS packets with destination callsign and path
- Receive APRS packets in real-time
- Support for position reports and text messages

### Packet Format

Send packets in JSON format:
```json
{
    "to": "DESTINATION",
    "via": "PATH",
    "data": "MESSAGE"
}
```

Receive packets in JSON format:
```json
{
    "from": "SOURCE",
    "to": "DESTINATION",
    "via": "PATH",
    "data": "MESSAGE"
}
```

## License

MIT License 