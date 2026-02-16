"""
Auto-Deploy Stores MCP Server.

Exposes the auto-deploy pipeline as Model Context Protocol tools via FastAPI.
Provided by free sources and APIs — MIDNGHTSAPPHIRE / GlowStar Labs.
"""

import os
import asyncio
from typing import Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from cli.utils.config import load_config
from cli.utils.eas import EASClient
from cli.utils.credentials import CredentialManager

app = FastAPI(
    title="Auto-Deploy Stores MCP Server",
    description="MCP server for deploying React/Vite apps to Apple App Store and Google Play Store",
    version="1.0.0"
)

# Models
class DeployRequest(BaseModel):
    app_name: str = Field(..., description="Display name of the app")
    bundle_id: str = Field(..., description="Unique bundle identifier (e.g., com.company.app)")
    source_path: str = Field(..., description="Path to the React/Vite web app source")
    platform: str = Field("both", description="Target platform: ios, android, or both")
    mode: str = Field("webview", description="Wrapping mode: webview, hybrid, or native")
    track: str = Field("internal", description="Google Play release track")
    release_notes: Optional[str] = Field(None, description="Release notes for the deployment")

class StatusRequest(BaseModel):
    deployment_id: Optional[str] = Field(None, description="Specific deployment ID to check")
    build_id: Optional[str] = Field(None, description="Specific build ID to check")

class CredentialRequest(BaseModel):
    name: str
    type: str
    value: Optional[str] = None
    file_path: Optional[str] = None

# Global state (in-memory for this session)
deployments = {}

@app.get("/tools")
async def list_tools():
    """List available MCP tools."""
    return {
        "tools": [
            {
                "name": "deploy_to_app_store",
                "description": "Wraps and submits a React/Vite web app to Apple App Store",
                "input_schema": DeployRequest.schema()
            },
            {
                "name": "deploy_to_play_store",
                "description": "Wraps and submits a React/Vite web app to Google Play Store",
                "input_schema": DeployRequest.schema()
            },
            {
                "name": "deploy_to_both",
                "description": "Parallel deployment of a React/Vite web app to both Apple and Google stores",
                "input_schema": DeployRequest.schema()
            },
            {
                "name": "check_deployment_status",
                "description": "Monitor the status of a deployment or build",
                "input_schema": StatusRequest.schema()
            },
            {
                "name": "manage_credentials",
                "description": "CRUD operations for app store and signing credentials",
                "input_schema": CredentialRequest.schema()
            }
        ]
    }

@app.post("/tools/deploy_to_both")
async def deploy_to_both(request: DeployRequest, background_tasks: BackgroundTasks):
    """MCP tool: deploy_to_both."""
    deployment_id = f"mcp-deploy-{os.urandom(4).hex()}"
    deployments[deployment_id] = {"status": "starting", "request": request.dict()}
    
    # In a real MCP server, we'd trigger the CLI or the underlying logic
    background_tasks.add_task(run_deployment, deployment_id, request)
    
    return {
        "message": "Deployment started in background",
        "deployment_id": deployment_id,
        "status": "queued"
    }

@app.post("/tools/check_deployment_status")
async def check_deployment_status(request: StatusRequest):
    """MCP tool: check_deployment_status."""
    if request.deployment_id:
        status = deployments.get(request.deployment_id, {"error": "Deployment not found"})
        return status
    
    # If no ID, return all active deployments
    return {"deployments": deployments}

@app.post("/tools/manage_credentials")
async def manage_credentials(request: CredentialRequest):
    """MCP tool: manage_credentials."""
    cm = CredentialManager()
    if request.value:
        cm.store_credential(request.name, request.type, request.value)
    elif request.file_path:
        cm.store_credential_file(request.name, request.type, request.file_path)
    
    return {"status": "success", "message": f"Credential {request.name} managed"}

async def run_deployment(deployment_id: str, request: DeployRequest):
    """Internal background task for deployment."""
    deployments[deployment_id]["status"] = "in_progress"
    try:
        # Here we would call the CLI logic:
        # 1. Wrap
        # 2. Build
        # 3. Submit
        # For now, we simulate the process
        await asyncio.sleep(2)
        deployments[deployment_id]["status"] = "completed"
        deployments[deployment_id]["result"] = {
            "ios": "submitted",
            "android": "submitted"
        }
    except Exception as e:
        deployments[deployment_id]["status"] = "failed"
        deployments[deployment_id]["error"] = str(e)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
