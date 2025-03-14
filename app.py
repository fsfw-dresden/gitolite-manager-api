import os
import time
import secrets
import base64
from fastapi import FastAPI, HTTPException, Depends, Request, Response, status, Security
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from typing import Dict, Optional, List, Any

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

# Initialize HTTP Basic Auth
security = HTTPBasic()

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

class AccessRight(BaseModel):
    permission: str = Field(..., description="Permission level (e.g., RW+)")
    users: List[str] = Field(..., description="List of users with this permission")

class RepositoryInfo(BaseModel):
    name: str = Field(..., description="Repository name")
    access_rights: List[AccessRight] = Field(..., description="Access rights for the repository")

class RepositoriesResponse(BaseModel):
    repositories: List[RepositoryInfo] = Field(..., description="List of repositories")

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """
    Verify HTTP Basic Auth credentials against environment variables.
    
    Returns:
        Username if credentials are valid
        
    Raises:
        HTTPException: If credentials are invalid
    """
    correct_username = os.environ.get("API_USERNAME", "admin")
    correct_password = os.environ.get("API_PASSWORD", "password")
    
    is_correct_username = secrets.compare_digest(credentials.username, correct_username)
    is_correct_password = secrets.compare_digest(credentials.password, correct_password)
    
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return credentials.username

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

@app.get("/gitolite/repos", response_model=RepositoriesResponse)
@limiter.limit(RATE_LIMIT)
async def list_gitolite_repos(
    request: Request,
    username: str = Depends(verify_credentials),
    gitolite_service: GitoliteService = Depends(get_gitolite_service)
):
    """
    List all Gitolite repositories and their access rights.
    
    This endpoint is secured with HTTP Basic Authentication.
    
    Returns:
        List of repositories with their access rights
    """
    try:
        repos_data = gitolite_service.list_repositories()
        
        # Transform the data to match the response model
        repositories = []
        for repo_name, access_rights in repos_data.items():
            repositories.append(
                RepositoryInfo(
                    name=repo_name,
                    access_rights=[
                        AccessRight(permission=ar["permission"], users=ar["users"])
                        for ar in access_rights
                    ]
                )
            )
        
        return RepositoriesResponse(repositories=repositories)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list repositories: {str(e)}")
