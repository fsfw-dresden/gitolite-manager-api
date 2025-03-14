import os
import time
from fastapi import FastAPI, HTTPException, Depends, Request, Response
from pydantic import BaseModel, Field
from typing import Dict, Optional

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from services.gitolite_service import GitoliteService, get_gitolite_service

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Initialize FastAPI app
app = FastAPI(
    title="Gitolite API",
    description="API for managing Gitolite repositories and SSH keys",
    version="0.1.0",
)

# Configure rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Rate limit configuration from environment variables
RATE_LIMIT = os.environ.get("RATE_LIMIT", "10/minute")

# Data models
class GitoliteRequest(BaseModel):
    ssh_pubkey: str = Field(..., description="SSH public key content")
    unit_name: str = Field(..., description="Learning unit name")
    username: str = Field(..., description="Username for repository access")

class GitoliteResponse(BaseModel):
    repo_url: str = Field(..., description="URL of the created repository")
    message: str = Field(..., description="Status message")

@app.put("/gitolite/repo", response_model=GitoliteResponse)
@limiter.limit("1/minute")
async def create_gitolite_repo(
    request: Request,
    gitolite_data: GitoliteRequest,
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
            gitolite_data.ssh_pubkey,
            gitolite_data.unit_name,
            gitolite_data.username
        )
        return GitoliteResponse(
            repo_url=repo_url,
            message="Repository created successfully"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create repository: {str(e)}")
