import os
import time
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, Optional

from services.gitolite_service import GitoliteService, get_gitolite_service

# Initialize FastAPI app
app = FastAPI(
    title="Gitolite API",
    description="API for managing Gitolite repositories and SSH keys",
    version="0.1.0",
)

# Data models
class GitoliteRequest(BaseModel):
    ssh_pubkey: str = Field(..., description="SSH public key content")
    unit_name: str = Field(..., description="Learning unit name")
    username: str = Field(..., description="Username for repository access")

class GitoliteResponse(BaseModel):
    repo_url: str = Field(..., description="URL of the created repository")
    message: str = Field(..., description="Status message")

@app.put("/gitolite/repo", response_model=GitoliteResponse)
async def create_gitolite_repo(
    request: GitoliteRequest,
    gitolite_service: GitoliteService = Depends(get_gitolite_service)
):
    """
    Create a new Gitolite repository with access for the provided SSH key.
    
    - Adds the SSH public key to the Gitolite keydir
    - Creates a new repository with RW+ access for the user
    - Returns the Git remote URL for the new repository
    """
    try:
        repo_url = gitolite_service.create_repo_with_key(
            request.ssh_pubkey,
            request.unit_name,
            request.username
        )
        return GitoliteResponse(
            repo_url=repo_url,
            message="Repository created successfully"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create repository: {str(e)}")
