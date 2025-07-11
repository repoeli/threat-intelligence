#!/usr/bin/env python3
"""
Setup script for Claude Desktop MCP integration
"""

import os
import json
import shutil
import sys
from pathlib import Path

def setup_claude_desktop_config():
    """Setup Claude Desktop configuration"""
    
    # Find Claude Desktop config directory
    if sys.platform == "win32":
        claude_config_dir = Path.home() / "AppData" / "Roaming" / "Claude"
    elif sys.platform == "darwin":  # macOS
        claude_config_dir = Path.home() / "Library" / "Application Support" / "Claude"
    else:  # Linux
        claude_config_dir = Path.home() / ".config" / "Claude"
    
    claude_config_dir.mkdir(parents=True, exist_ok=True)
    config_file = claude_config_dir / "claude_desktop_config.json"
    
    # Load our MCP server config
    mcp_config_file = Path(__file__).parent / "claude_desktop_config.json"
    
    if not mcp_config_file.exists():
        print(f"❌ MCP config file not found: {mcp_config_file}")
        return False
    
    with open(mcp_config_file, 'r') as f:
        mcp_config = json.load(f)
    
    # Update paths to be absolute
    current_dir = Path(__file__).parent.parent.absolute()
    mcp_config["mcpServers"]["threat-intelligence"]["args"][0] = str(current_dir / "mcp-server" / "server.py")
    
    # Load existing Claude config or create new
    existing_config = {}
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                existing_config = json.load(f)
        except json.JSONDecodeError:
            print("⚠️ Existing Claude config is invalid, creating new one")
    
    # Merge configurations
    if "mcpServers" not in existing_config:
        existing_config["mcpServers"] = {}
    
    existing_config["mcpServers"].update(mcp_config["mcpServers"])
    
    # Write updated config
    try:
        with open(config_file, 'w') as f:
            json.dump(existing_config, f, indent=2)
        
        print(f"✅ Claude Desktop configuration updated: {config_file}")
        print("\n📝 Configuration added:")
        print(json.dumps(mcp_config, indent=2))
        return True
        
    except Exception as e:
        print(f"❌ Failed to write Claude config: {e}")
        return False

def install_requirements():
    """Install MCP server requirements"""
    import subprocess
    
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    if not requirements_file.exists():
        print(f"❌ Requirements file not found: {requirements_file}")
        return False
    
    try:
        print("🔧 Installing MCP server requirements...")
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ], check=True, capture_output=True, text=True)
        
        print("✅ Requirements installed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install requirements: {e}")
        print(f"Error output: {e.stderr}")
        return False

def check_environment_variables():
    """Check if required environment variables are set"""
    required_vars = [
        "VIRUSTOTAL_API_KEY",
        "OPENAI_API_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️ Missing environment variables: {missing_vars}")
        print("\n📋 Please set these variables in your .env file or environment:")
        for var in missing_vars:
            print(f"   {var}=your_api_key_here")
        print("\n💡 Copy your API keys to the Claude Desktop config or .env file")
        return False
    
    print("✅ All required environment variables are set")
    return True

def main():
    """Main setup function"""
    print("🚀 Setting up Claude Desktop MCP Integration for Threat Intelligence")
    print("=" * 70)
    
    # Step 1: Install requirements
    if not install_requirements():
        print("❌ Setup failed at requirements installation")
        return False
    
    # Step 2: Setup Claude Desktop config
    if not setup_claude_desktop_config():
        print("❌ Setup failed at Claude Desktop configuration")
        return False
    
    # Step 3: Check environment variables
    env_ok = check_environment_variables()
    
    print("\n" + "=" * 70)
    print("🎉 MCP Server Setup Complete!")
    print("\n📋 Next Steps:")
    print("1. ✅ MCP server code is ready")
    print("2. ✅ Claude Desktop configuration updated")
    print("3. ✅ Requirements installed")
    
    if not env_ok:
        print("4. ⚠️ Configure API keys in Claude Desktop config")
    else:
        print("4. ✅ Environment variables configured")
    
    print("\n🔄 To activate:")
    print("1. Restart Claude Desktop")
    print("2. Look for 'threat-intelligence' tools in Claude")
    print('3. Use commands like: "Analyze domain example.com"')
    
    print("\n🛠️ Available Tools:")
    print('- validate_domain: Check if domain format is valid')
    print('- analyze_domain: Full threat intelligence analysis')
    print('- analyze_ip: IP address threat analysis') 
    print('- analyze_url: URL threat analysis')
    print('- enrich_with_ai: Get GPT expert insights')
    
    print('\n💬 Example Commands:')
    print('  "Analyze domain google.com"')
    print('  "Validate domain example.com"')
    print('  "Analyze IP 8.8.8.8"')
    print('  "Analyze URL https://suspicious-site.com"')
    print('  "Enrich with AI <indicator> <data> What are the security implications?"')
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
