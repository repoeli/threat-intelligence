#!/usr/bin/env python3
"""
Threat Intelligence MCP Server
Provides threat analysis capabilities to Claude Desktop via Model Context Protocol
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Sequence

# Add parent directory to path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)

# Import our existing threat intelligence modules
from backend.app.services.threat_analysis import threat_analysis_service
from backend.app.services.virustotal_service import vt_call
from backend.app.utils.indicator import determine_indicator_type
from backend.app.models import IndicatorType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("threat-intel-mcp")

# Initialize MCP Server
server = Server("threat-intelligence-mcp")

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available threat intelligence tools"""
    return [
        Tool(
            name="analyze_domain",
            description="Analyze a domain name for threat intelligence using VirusTotal and other sources",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Domain name to analyze (e.g., example.com)"
                    },
                    "include_raw_data": {
                        "type": "boolean", 
                        "description": "Include raw API responses",
                        "default": False
                    }
                },
                "required": ["domain"]
            }
        ),
        Tool(
            name="analyze_ip",
            description="Analyze an IP address for threat intelligence",
            inputSchema={
                "type": "object",
                "properties": {
                    "ip": {
                        "type": "string",
                        "description": "IP address to analyze (e.g., 8.8.8.8)"
                    },
                    "include_raw_data": {
                        "type": "boolean",
                        "description": "Include raw API responses", 
                        "default": False
                    }
                },
                "required": ["ip"]
            }
        ),
        Tool(
            name="analyze_url", 
            description="Analyze a URL for threat intelligence",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to analyze (e.g., https://example.com)"
                    },
                    "include_raw_data": {
                        "type": "boolean",
                        "description": "Include raw API responses",
                        "default": False
                    }
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="validate_domain",
            description="Validate if a domain name is properly formatted and exists",
            inputSchema={
                "type": "object", 
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Domain name to validate"
                    }
                },
                "required": ["domain"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls from Claude"""
    try:
        if name == "validate_domain":
            domain = arguments["domain"]
            
            # Use our existing domain validation logic
            try:
                indicator_type = determine_indicator_type(domain)
                if indicator_type == "domain":
                    return [TextContent(
                        type="text",
                        text=f"✅ Domain '{domain}' is valid and properly formatted."
                    )]
                else:
                    return [TextContent(
                        type="text", 
                        text=f"❌ '{domain}' is not a valid domain. Detected as: {indicator_type}"
                    )]
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"❌ Domain validation failed: {str(e)}"
                )]
                
        elif name == "analyze_domain":
            domain = arguments["domain"]
            include_raw = arguments.get("include_raw_data", False)
            
            # Perform comprehensive domain analysis
            result = await threat_analysis_service.analyze_indicator(
                indicator=domain,
                user_id="mcp_user",
                subscription="admin",  # Give MCP admin privileges
                include_raw=include_raw
            )
            
            # Format the analysis result for Claude
            analysis_text = format_analysis_result(result, "domain")
            
            return [TextContent(
                type="text",
                text=analysis_text
            )]
            
        elif name == "analyze_ip":
            ip = arguments["ip"]
            include_raw = arguments.get("include_raw_data", False)
            
            result = await threat_analysis_service.analyze_indicator(
                indicator=ip,
                user_id="mcp_user", 
                subscription="admin",
                include_raw=include_raw
            )
            
            analysis_text = format_analysis_result(result, "IP address")
            
            return [TextContent(
                type="text",
                text=analysis_text
            )]
            
        elif name == "analyze_url":
            url = arguments["url"]
            include_raw = arguments.get("include_raw_data", False)
            
            result = await threat_analysis_service.analyze_indicator(
                indicator=url,
                user_id="mcp_user",
                subscription="admin", 
                include_raw=include_raw
            )
            
            analysis_text = format_analysis_result(result, "URL")
            
            return [TextContent(
                type="text",
                text=analysis_text
            )]
            
        else:
            return [TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]
            
    except Exception as e:
        logger.error(f"Error in tool {name}: {str(e)}")
        return [TextContent(
            type="text",
            text=f"Error analyzing indicator: {str(e)}"
        )]

def format_analysis_result(result, indicator_type: str) -> str:
    """Format analysis result for Claude consumption"""
    
    threat_level_emoji = {
        "SAFE": "🟢",
        "LOW": "🟡", 
        "MEDIUM": "🟠",
        "HIGH": "🔴",
        "CRITICAL": "🚨"
    }
    
    emoji = threat_level_emoji.get(result.threat_score.threat_level.value, "❓")
    
    analysis = f"""
# 🛡️ Threat Intelligence Analysis: {result.indicator}

## 📊 Summary
- **Indicator Type**: {indicator_type}
- **Threat Level**: {emoji} {result.threat_score.threat_level.value}
- **Overall Score**: {result.threat_score.overall_score:.2f}/1.0
- **Confidence**: {result.threat_score.confidence:.2f}/1.0
- **Status**: {result.status.value}

## 🔍 Detection Results
- **Detection Ratio**: {getattr(result, 'detection_ratio', 'N/A')}
- **Reputation**: {getattr(result, 'reputation', 'Unknown')}

## 🌍 Additional Information
"""

    # Add geolocation if available
    if hasattr(result, 'geolocation') and result.geolocation:
        geo = result.geolocation
        analysis += f"""
### 📍 Geolocation
- **Country**: {geo.get('country', 'Unknown')}
- **City**: {geo.get('city', 'Unknown')}
- **ISP**: {geo.get('as_owner', 'Unknown')}
"""

    # Add vendor analysis if available
    if hasattr(result, 'vendor_results') and result.vendor_results:
        analysis += "\n### 🔬 Vendor Analysis\n"
        for vendor_name, vendor_result in result.vendor_results.items():
            status = "✅" if vendor_result.status == "completed" else "❌"
            analysis += f"- **{vendor_name}**: {status} Score: {vendor_result.score:.2f}\n"

    # Add threat factors if available  
    if result.threat_score.factors:
        analysis += "\n### ⚠️ Threat Factors\n"
        for factor, value in result.threat_score.factors.items():
            analysis += f"- **{factor}**: {value}\n"

    # Add metadata
    if hasattr(result, 'metadata') and result.metadata:
        analysis += f"\n### 📋 Analysis Metadata\n"
        analysis += f"- **Analysis ID**: {result.metadata.get('analysis_id', 'N/A')}\n"
        analysis += f"- **Processing Time**: {result.metadata.get('processing_time_ms', 'N/A')}ms\n"

    analysis += f"\n---\n*Analysis completed at {result.metadata.get('timestamp', 'Unknown time')}*"
    
    return analysis

async def main():
    """Main entry point for the MCP server"""
    logger.info("Starting Threat Intelligence MCP Server...")
    
    # Load environment variables for API keys
    from dotenv import load_dotenv
    load_dotenv()
    
    # Verify required environment variables
    required_vars = ["VIRUSTOTAL_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        sys.exit(1)
    
    logger.info("Environment variables loaded successfully")
    logger.info("MCP Server ready for connections...")
    
    # Run the stdio server
    async with stdio_server() as streams:
        await server.run(
            streams[0], streams[1], InitializationOptions(
                server_name="threat-intelligence-mcp",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None,
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
