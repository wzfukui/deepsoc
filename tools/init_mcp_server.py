import sys
import os
from flask import Flask
from app.models import db, MCPServer
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def init_mcp_server():
    with app.app_context():
        # Check if server already exists
        server_key = "USGFirewall"
        existing = MCPServer.query.filter_by(server_key=server_key).first()
        if existing:
            print(f"MCP Server {server_key} already exists.")
            return

        new_server = MCPServer(
            server_key=server_key,
            name="华为USG防火墙",
            description="公司部署在边界的华为USG防火墙，可用于拦截内外部通讯。",
            transport_type="streamableHttp",
            base_url="https://mcp.51pwd.com/Firewall/USGFirewall?token=75cef760-a70d-412e-8481-fdc699e4c7d8",
            status="enabled",
            timeout=30
        )
        db.session.add(new_server)
        db.session.commit()
        print(f"MCP Server {server_key} initialized successfully.")

if __name__ == "__main__":
    init_mcp_server()
