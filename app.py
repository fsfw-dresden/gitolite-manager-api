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
    username: str = Field(..., description="Username that was used for repository access")
    message: str = Field(..., description="Status message")

class AccessRight(BaseModel):
    permission: str = Field(..., description="Permission level (e.g., RW+)")
    users: List[str] = Field(..., description="List of users with this permission")

class RepositoryInfo(BaseModel):
    name: str = Field(..., description="Repository name")
    access_rights: List[AccessRight] = Field(..., description="Access rights for the repository")

class RepositoriesResponse(BaseModel):
    repositories: List[RepositoryInfo] = Field(..., description="List of repositories")

class PublicAccessRequest(BaseModel):
    repo_name: str = Field(..., description="Name of the repository")
    enable: bool = Field(..., description="True to enable public access, False to disable")

class PublicAccessResponse(BaseModel):
    repo_name: str = Field(..., description="Name of the repository")
    public_access: bool = Field(..., description="Current public access status")
    message: str = Field(..., description="Status message")

class SubmoduleRequest(BaseModel):
    repo_url: str = Field(..., description="Git repository URL to add as submodule")
    path: Optional[str] = Field(None, description="Path within the master repository (defaults to repo name)")

class SubmoduleResponse(BaseModel):
    repo_url: str = Field(..., description="Git repository URL of the submodule")
    path: str = Field(..., description="Path of the submodule within the master repository")
    status: str = Field(..., description="Status of the operation (added/updated)")
    message: str = Field(..., description="Status message")

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
    - If the key already exists, uses the existing username
    - If the username exists but the key is new, generates a unique username
    - Creates a new repository with RW+ access for the user
    - Returns the Git remote URL for the new repository and the username that was used
    """
    try:
        result = gitolite_service.create_repo_with_key(
            gitolite_data.ssh_pubkey,
            gitolite_data.unit_name,
            gitolite_data.username
        )
        return GitoliteResponse(
            repo_url=result["remote_url"],
            username=result["username"],
            message="Repository created successfully"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create repository: {str(e)}")

@app.get("/gitolite/repos", response_model=RepositoriesResponse)
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

@app.post("/gitolite/repo/public-access", response_model=PublicAccessResponse)
async def set_repo_public_access(
    request: Request,
    access_data: PublicAccessRequest,
    username: str = Depends(verify_credentials),
    gitolite_service: GitoliteService = Depends(get_gitolite_service)
):
    """
    Enable or disable public read access to a repository.
    
    This endpoint is secured with HTTP Basic Authentication.
    
    - When enabled, adds 'R = @all' to the repository configuration
    - When disabled, removes 'R = @all' from the repository configuration
    
    Args:
        access_data: Repository name and access flag
        
    Returns:
        Updated public access status
    """
    try:
        repo_name = access_data.repo_name
        enable = access_data.enable
        
        # Check if repository exists
        repos = gitolite_service.list_repositories()
        if repo_name not in repos:
            raise HTTPException(
                status_code=404, 
                detail=f"Repository '{repo_name}' not found"
            )
        
        # Set public access
        result = gitolite_service.set_public_access(repo_name, enable)
        
        return PublicAccessResponse(
            repo_name=repo_name,
            public_access=result,
            message=f"Public access {'enabled' if result else 'disabled'} for repository '{repo_name}'"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to update public access: {str(e)}"
        )

@app.post("/gitolite/submodule", response_model=SubmoduleResponse)
async def manage_submodule(
    request: Request,
    submodule_data: SubmoduleRequest,
    username: str = Depends(verify_credentials),
    gitolite_service: GitoliteService = Depends(get_gitolite_service)
):
    """
    Add or update a git repository as a submodule to the master repository.
    
    This endpoint is secured with HTTP Basic Authentication.
    
    - If the submodule doesn't exist, it will be added
    - If the submodule already exists, it will be updated to the latest version
    
    Args:
        submodule_data: Repository URL and optional path
        
    Returns:
        Status of the submodule operation
    """
    try:
        repo_url = submodule_data.repo_url
        path = submodule_data.path
        
        # Add or update the submodule
        result = gitolite_service.manage_submodule(repo_url, path)
        
        return SubmoduleResponse(
            repo_url=repo_url,
            path=result["path"],
            status=result["status"],
            message=result["message"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to manage submodule: {str(e)}"
        )
