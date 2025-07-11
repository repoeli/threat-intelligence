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
from pathlib import Path

# Add parent directory to path to import our modules
project_root = Path(__file__).parent.parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Add backend directory to path  
backend_path = project_root / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

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
try:
    from backend.app.services.threat_analysis import threat_analysis_service
    from backend.app.services.virustotal_service import vt_call
    from backend.app.utils.indicator import determine_indicator_type
    from backend.app.models import IndicatorType
    BACKEND_AVAILABLE = True
    logger = logging.getLogger("threat-intel-mcp")
    logger.info("Backend modules imported successfully")
except ImportError as e:
    logger = logging.getLogger("threat-intel-mcp")
    logger.error(f"Failed to import backend modules: {e}")
    logger.error(f"Current working directory: {os.getcwd()}")
    logger.error(f"Python path: {sys.path[:3]}...")
    BACKEND_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
if 'logger' not in locals():
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
        ),
        Tool(
            name="enrich_with_ai",
            description="Ask GPT to analyze and enrich threat intelligence data with expert insights",
            inputSchema={
                "type": "object",
                "properties": {
                    "indicator": {
                        "type": "string", 
                        "description": "The indicator (IP, domain, URL) to get AI insights about"
                    },
                    "analysis_data": {
                        "type": "string",
                        "description": "Raw threat intelligence data to analyze"
                    },
                    "question": {
                        "type": "string",
                        "description": "Specific question to ask GPT about the indicator",
                        "default": "What do you know about this indicator? Provide expert cybersecurity analysis."
                    }
                },
                "required": ["indicator", "analysis_data"]
            }
        )
    ]

@server.list_resources()
async def handle_list_resources() -> list[Resource]:
    """List available resources (none for this server)"""
    return []

@server.list_prompts()
async def handle_list_prompts():
    """List available prompts (none for this server)"""
    return []

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls from Claude"""
    try:
        if name == "validate_domain":
            domain = arguments["domain"]
            
            # Use our existing domain validation logic
            try:
                indicator_type = determine_indicator_type(domain)
                if indicator_type == "domain":                return [TextContent(
                    type="text",
                    text=f"[SUCCESS] Domain '{domain}' is valid and properly formatted."
                )]
                else:
                    return [TextContent(
                        type="text", 
                        text=f"❌ '{domain}' is not a valid domain. Detected as: {indicator_type}"
                    )]
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"[ERROR] Domain validation failed: {str(e)}"
                )]
                
        elif name == "analyze_domain":
            domain = arguments["domain"]
            include_raw = arguments.get("include_raw_data", False)
            
            if not BACKEND_AVAILABLE:
                return [TextContent(
                    type="text",
                    text=f"[ERROR] Backend services not available. Please check if the threat intelligence API is running and accessible."
                )]
            
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
            
        elif name == "enrich_with_ai":
            indicator = arguments["indicator"]
            analysis_data = arguments["analysis_data"]
            question = arguments.get("question", "What do you know about this indicator? Provide expert cybersecurity analysis.")
            
            # Call GPT for enrichment
            enriched_analysis = await enrich_with_gpt(indicator, analysis_data, question)
            
            return [TextContent(
                type="text",
                text=enriched_analysis
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
    
    threat_level_text = {
        "SAFE": "[SAFE]",
        "LOW": "[LOW]", 
        "MEDIUM": "[MEDIUM]",
        "HIGH": "[HIGH]",
        "CRITICAL": "[CRITICAL]"
    }
    
    level_indicator = threat_level_text.get(getattr(result.threat_score.threat_level, 'value', 'UNKNOWN'), "[UNKNOWN]")
    
    analysis = f"""
# Threat Intelligence Analysis: {result.indicator}

## Summary
- **Indicator Type**: {indicator_type}
- **Threat Level**: {level_indicator}
- **Overall Score**: {result.threat_score.overall_score:.2f}/1.0
- **Confidence**: {result.threat_score.confidence:.2f}/1.0
- **Status**: {getattr(result.status, 'value', 'Unknown')}

## Detection Results
- **Detection Ratio**: {getattr(result, 'detection_ratio', 'N/A')}
- **Reputation**: {getattr(result, 'reputation', 'Unknown')}

## Additional Information
"""

    # Add geolocation if available
    if hasattr(result, 'geolocation') and result.geolocation:
        geo = result.geolocation
        analysis += f"""
### Geolocation
- **Country**: {geo.get('country', 'Unknown') if isinstance(geo, dict) else getattr(geo, 'country', 'Unknown')}
- **City**: {geo.get('city', 'Unknown') if isinstance(geo, dict) else getattr(geo, 'city', 'Unknown')}
- **ISP**: {geo.get('as_owner', 'Unknown') if isinstance(geo, dict) else getattr(geo, 'as_owner', 'Unknown')}
"""

    # Add vendor analysis if available
    if hasattr(result, 'vendor_results') and result.vendor_results:
        analysis += "\n### Vendor Analysis\n"
        
        # Handle both dict and list formats for vendor_results
        if isinstance(result.vendor_results, dict):
            for vendor_name, vendor_result in result.vendor_results.items():
                status = "[COMPLETED]" if getattr(vendor_result, 'status', None) == "completed" else "[PENDING]"
                score = getattr(vendor_result, 'score', 0)
                analysis += f"- **{vendor_name}**: {status} Score: {score:.2f}\n"
        elif isinstance(result.vendor_results, list):
            for vendor_result in result.vendor_results:
                vendor_name = getattr(vendor_result, 'name', 'Unknown Vendor')
                status = "[COMPLETED]" if getattr(vendor_result, 'status', None) == "completed" else "[PENDING]"
                score = getattr(vendor_result, 'score', 0)
                analysis += f"- **{vendor_name}**: {status} Score: {score:.2f}\n"

    # Add threat factors if available  
    if hasattr(result, 'threat_score') and hasattr(result.threat_score, 'factors') and result.threat_score.factors:
        analysis += "\n### Threat Factors\n"
        factors = result.threat_score.factors
        if isinstance(factors, dict):
            for factor, value in factors.items():
                analysis += f"- **{factor}**: {value}\n"
        else:
            analysis += f"- **Factors**: {factors}\n"

    # Add metadata
    if hasattr(result, 'metadata') and result.metadata:
        analysis += f"\n### Analysis Metadata\n"
        metadata = result.metadata
        if isinstance(metadata, dict):
            analysis += f"- **Analysis ID**: {metadata.get('analysis_id', 'N/A')}\n"
            analysis += f"- **Processing Time**: {metadata.get('processing_time_ms', 'N/A')}ms\n"
        else:
            analysis += f"- **Metadata**: {metadata}\n"

    timestamp = "Unknown time"
    if hasattr(result, 'metadata') and result.metadata and isinstance(result.metadata, dict):
        timestamp = result.metadata.get('timestamp', 'Unknown time')
    
    analysis += f"\n---\n*Analysis completed at {timestamp}*"
    
    return analysis

async def enrich_with_gpt(indicator: str, analysis_data: str, question: str) -> str:
    """Use GPT to enrich threat intelligence analysis"""
    try:
        import openai
        
        # Get OpenAI API key
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            return "[ERROR] OpenAI API key not configured for AI enrichment"
        
        client = openai.AsyncOpenAI(api_key=openai_key)
        
        # Create a comprehensive prompt for GPT
        prompt = f"""You are a cybersecurity expert analyzing threat intelligence data. 

INDICATOR TO ANALYZE: {indicator}

TECHNICAL DATA:
{analysis_data}

QUESTION: {question}

Please provide:
1. Expert analysis of this indicator's threat level and behavior
2. Potential attack vectors or malicious activities associated with it
3. Recommendations for security teams
4. Context about any known campaigns, malware families, or threat actors
5. Defensive measures and indicators to monitor

Format your response in a clear, professional manner suitable for cybersecurity professionals."""

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a world-class cybersecurity threat intelligence analyst with deep expertise in malware analysis, threat hunting, and digital forensics."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.3
        )
        
        ai_analysis = response.choices[0].message.content
        
        return f"""
# 🤖 AI-Enhanced Threat Analysis

## 🧠 GPT Expert Insights for: {indicator}

{ai_analysis}

---
*AI analysis powered by GPT-4o-mini | Generated at {os.getenv('TIMESTAMP', 'unknown time')}*
"""
        
    except Exception as e:
        logger.error(f"GPT enrichment error: {str(e)}")
        return f"❌ AI enrichment failed: {str(e)}"

async def main():
    """Main entry point for the MCP server"""
    logger.info("Starting Threat Intelligence MCP Server...")
    
    # Load environment variables - check both locations
    from dotenv import load_dotenv
    import os
    from pathlib import Path
    
    # Try to load from multiple locations
    env_locations = [
        Path(__file__).parent / ".env",  # mcp-server/.env
        Path(__file__).parent.parent / ".env",  # project root .env
        Path(__file__).parent.parent / "backend" / ".env",  # backend/.env
    ]
    
    for env_file in env_locations:
        if env_file.exists():
            load_dotenv(env_file)
            logger.info(f"Loaded environment from: {env_file}")
            break
    else:
        # No .env file found, but environment variables might be set by Claude Desktop
        logger.info("No .env file found, using system environment variables")
    
    # Verify required environment variables
    required_vars = ["VIRUSTOTAL_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.info("Please ensure API keys are set in:")
        logger.info("1. Claude Desktop config (when running via Claude)")
        logger.info("2. .env file in mcp-server/ directory (for testing)")
        logger.info("3. System environment variables")
        sys.exit(1)
    
    logger.info("Environment variables loaded successfully")
    logger.info(f"VirusTotal API key: {'[SET]' if os.getenv('VIRUSTOTAL_API_KEY') else '[MISSING]'}")
    logger.info(f"OpenAI API key: {'[SET]' if os.getenv('OPENAI_API_KEY') else '[MISSING]'}")
    logger.info("MCP Server ready for connections...")
    
    # Run the stdio server
    async with stdio_server() as streams:
        from mcp.types import ServerCapabilities
        capabilities = ServerCapabilities(
            tools={},
            resources={}
        )
        
        await server.run(
            streams[0], streams[1], InitializationOptions(
                server_name="threat-intelligence-mcp",
                server_version="1.0.0",
                capabilities=capabilities
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
