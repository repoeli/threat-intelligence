# Threat Intelligence MCP Server

A Model Context Protocol (MCP) server that provides threat intelligence analysis capabilities to Claude Desktop.

## Features

- 🔍 **Domain Analysis**: Comprehensive domain threat intelligence
- 🌐 **IP Analysis**: IP address reputation and geolocation  
- 🔗 **URL Analysis**: URL safety and reputation checking
- ✅ **Domain Validation**: Check domain format and validity
- 🛡️ **Multi-Source Intelligence**: VirusTotal integration with extensible architecture

## Installation

### Prerequisites

1. **Claude Desktop** - Download and install from Anthropic
2. **Python 3.11+** - Required for async/await support
3. **Environment Variables** - VirusTotal API key required

### Setup

1. **Install Dependencies**:
```bash
pip install mcp python-dotenv
```

2. **Configure Environment**:
Create a `.env` file in the threat-intelligence directory:
```bash
VIRUSTOTAL_API_KEY=your_virustotal_api_key_here
JWT_SECRET_KEY=your_secret_key_here
```

3. **Configure Claude Desktop**:
Add this to your Claude Desktop configuration:

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "threat-intelligence": {
      "command": "python",
      "args": ["C:\\threat-intelligence\\mcp-server\\server.py"],
      "env": {
        "VIRUSTOTAL_API_KEY": "your_virustotal_api_key_here"
      }
    }
  }
}
```

## Usage

Once configured, you can use these commands in Claude Desktop:

### Domain Analysis
```
Please analyze the domain "suspicious-site.com" for threats
```

### IP Analysis  
```
Can you check the reputation of IP address 192.168.1.1?
```

### URL Analysis
```
Analyze this URL for safety: https://example.com/suspicious-page
```

### Domain Validation
```
Is "test..domain" a valid domain name?
```

## API Integration

The MCP server integrates with your existing threat intelligence platform:

- **Backend API**: http://localhost:8686
- **Database**: PostgreSQL with analysis history
- **Authentication**: JWT-based with admin privileges for MCP
- **Rate Limiting**: Managed through existing quota system

## Architecture

```
Claude Desktop
    ↓ (MCP Protocol)
MCP Server (server.py)
    ↓ (Internal API)
Threat Analysis Service
    ↓ (External APIs)
VirusTotal + Other Sources
```

## Development

### Testing the MCP Server

1. **Direct Testing**:
```bash
cd c:\threat-intelligence\mcp-server
python server.py
```

2. **With Claude Desktop**:
- Open Claude Desktop
- Try commands like "analyze domain google.com"
- Check for threat intelligence responses

### Adding New Tools

To add new analysis capabilities:

1. Add tool definition in `handle_list_tools()`
2. Add tool implementation in `handle_call_tool()`
3. Update documentation

### Debugging

Enable debug logging:
```python
logging.basicConfig(level=logging.DEBUG)
```

Check Claude Desktop logs:
- **Windows**: `%APPDATA%\Claude\logs\`
- **macOS**: `~/Library/Logs/Claude/`

## Error Handling

The server includes comprehensive error handling:

- **Invalid domains**: Graceful validation with helpful messages
- **API failures**: Fallback responses with error details
- **Missing credentials**: Clear error messages for setup issues
- **Network issues**: Timeout handling and retry logic

## Security

- **Environment Variables**: Sensitive data stored in environment
- **Admin Privileges**: MCP user has admin-level access to analysis APIs
- **Input Validation**: All inputs validated before processing
- **Error Sanitization**: No sensitive data leaked in error messages

## Next Steps

1. **Enhanced GPT Integration**: Add OpenAI analysis to MCP responses
2. **Bulk Analysis**: Support for multiple indicators at once  
3. **Custom Prompts**: Allow Claude to customize analysis depth
4. **Export Capabilities**: Generate reports and export results
5. **Real-time Updates**: WebSocket integration for live analysis
