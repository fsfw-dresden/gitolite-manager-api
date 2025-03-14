import os
import time
import re
import subprocess
from pathlib import Path
from typing import Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GitoliteService:
    """Service for managing Gitolite repositories and SSH keys."""
    
    def __init__(self, gitolite_root: str, gitolite_url: str):
        """
        Initialize the GitoliteService.
        
        Args:
            gitolite_root: Path to the Gitolite admin repository
            gitolite_url: Base URL for Gitolite server (e.g., 'git@example.com')
        """
        self.gitolite_root = Path(gitolite_root)
        self.keydir = self.gitolite_root / "keydir"
        self.config_file = self.gitolite_root / "conf" / "gitolite.conf"
        self.gitolite_url = gitolite_url
    
    def _slugify(self, text: str) -> str:
        """
        Convert text to a URL-friendly slug.
        
        Args:
            text: Text to slugify
            
        Returns:
            Slugified text
        """
        # Convert to lowercase and replace spaces with underscores
        slug = text.lower().strip().replace(' ', '_')
        # Remove special characters
        slug = re.sub(r'[^a-z0-9_-]', '', slug)
        return slug
    
    def _key_exists(self, username: str) -> bool:
        """
        Check if a key already exists for the given username.
        
        Args:
            username: Username to check
            
        Returns:
            True if key exists, False otherwise
        """
        slugged_username = self._slugify(username)
        key_path = self.keydir / f"{slugged_username}.pub"
        return key_path.exists()
    
    def _add_ssh_key(self, username: str, ssh_pubkey: str) -> str:
        """
        Add an SSH public key to the Gitolite keydir.
        
        Args:
            username: Username for the key
            ssh_pubkey: SSH public key content
            
        Returns:
            Slugified username
            
        Raises:
            ValueError: If the key already exists
        """
        slugged_username = self._slugify(username)
        
        if self._key_exists(username):
            raise ValueError(f"SSH key for user '{username}' already exists")
        
        key_path = self.keydir / f"{slugged_username}.pub"
        
        # Write the key to the file
        with open(key_path, 'w') as f:
            f.write(ssh_pubkey.strip() + '\n')
        
        # Add the key to git
        self._run_git_command(["add", str(key_path.relative_to(self.gitolite_root))])
        
        return slugged_username
    
    def _add_repo_to_config(self, repo_name: str, username: str) -> None:
        """
        Add a repository configuration to gitolite.conf.
        
        Args:
            repo_name: Name of the repository
            username: Username to grant access to
        """
        # Read the current config
        with open(self.config_file, 'r') as f:
            config_content = f.read()
        
        # Append the new repo configuration
        repo_config = f"\nrepo {repo_name}\n    RW+     =   {username}\n"
        
        with open(self.config_file, 'a') as f:
            f.write(repo_config)
        
        # Add the config to git
        self._run_git_command(["add", str(self.config_file.relative_to(self.gitolite_root))])
    
    def parse_gitolite_config(self):
        """
        Parse the gitolite.conf file to extract repository information.
        
        Returns:
            A dictionary mapping repository names to their access rights
        """
        repos = {}
        current_repo = None
        
        with open(self.config_file, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Check for repo definition
                repo_match = re.match(r'^repo\s+(.+)$', line)
                if repo_match:
                    current_repo = repo_match.group(1)
                    repos[current_repo] = []
                    continue
                
                # Check for access rights if we're in a repo block
                if current_repo and line:
                    # Match access pattern like "RW+ = user1 user2"
                    access_match = re.match(r'^\s*([RW+-]+)\s*=\s*(.+)$', line)
                    if access_match:
                        permission = access_match.group(1)
                        users = [u.strip() for u in access_match.group(2).split()]
                        repos[current_repo].append({
                            "permission": permission,
                            "users": users
                        })
        
        return repos
    
    def has_public_access(self, repo_name):
        """
        Check if a repository has public read access (@all).
        
        Args:
            repo_name: Name of the repository
            
        Returns:
            True if the repository has public read access, False otherwise
        """
        repos = self.parse_gitolite_config()
        
        if repo_name not in repos:
            return False
        
        for access in repos[repo_name]:
            if access["permission"] == "R" and "@all" in access["users"]:
                return True
        
        return False
    
    def list_repositories(self):
        """
        List all repositories and their access rights.
        
        Returns:
            Dictionary with repository information
        """
        return self.parse_gitolite_config()
    
    def set_public_access(self, repo_name, enable):
        """
        Enable or disable public read access to a repository.
        
        Args:
            repo_name: Name of the repository
            enable: True to enable public access, False to disable
            
        Returns:
            Current public access status after the operation
            
        Raises:
            ValueError: If the repository doesn't exist
        """
        # Check if repository exists
        repos = self.parse_gitolite_config()
        if repo_name not in repos:
            raise ValueError(f"Repository '{repo_name}' not found")
        
        # Check current public access status
        current_status = self.has_public_access(repo_name)
        
        # If status already matches the requested state, no changes needed
        if current_status == enable:
            return current_status
        
        # Read the current config file
        with open(self.config_file, 'r') as f:
            lines = f.readlines()
        
        # Process the file to add or remove public access
        in_target_repo = False
        public_access_line_index = -1
        repo_end_index = -1
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Find the repository section
            if stripped.startswith(f"repo {repo_name}"):
                in_target_repo = True
                continue
            
            # If we're in the target repo section
            if in_target_repo:
                # Check for public access line
                if stripped == "R     =   @all":
                    public_access_line_index = i
                
                # Check for the end of the repo section (next repo or end of file)
                if stripped.startswith("repo ") or i == len(lines) - 1:
                    repo_end_index = i
                    break
        
        # Modify the file based on the requested action
        if enable and public_access_line_index == -1:
            # Add public access
            if repo_end_index != -1:
                # Insert before the next repo or at the end of the file
                lines.insert(repo_end_index, "    R     =   @all\n")
            else:
                # Append to the end of the file (should not happen with proper parsing)
                lines.append("    R     =   @all\n")
        elif not enable and public_access_line_index != -1:
            # Remove public access
            lines.pop(public_access_line_index)
        
        # Write the modified config back to the file
        with open(self.config_file, 'w') as f:
            f.writelines(lines)
        
        # Commit and push the changes
        self._run_git_command(["add", str(self.config_file.relative_to(self.gitolite_root))])
        self._run_git_command(["commit", "-m", f"{'Enable' if enable else 'Disable'} public access for {repo_name}"])
        self._run_git_command(["push", "origin", "master"])
        
        # Return the new status
        return enable
    
    def _run_git_command(self, args: list) -> str:
        """
        Run a git command in the gitolite admin repository.
        
        Args:
            args: Git command arguments
            
        Returns:
            Command output
            
        Raises:
            Exception: If the command fails
        """
        cmd = ["git", "-C", str(self.gitolite_root)] + args
        logger.info(f"Running git command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {e.stderr}")
            raise Exception(f"Git command failed: {e.stderr}")
    
    def create_repo_with_key(self, ssh_pubkey: str, unit_name: str, username: str) -> str:
        """
        Create a new Gitolite repository with access for the provided SSH key.
        
        Args:
            ssh_pubkey: SSH public key content
            unit_name: Learning unit name
            username: Username for repository access
            
        Returns:
            Git remote URL for the new repository
            
        Raises:
            ValueError: If the key already exists
            Exception: If any git operation fails
        """
        # Add the SSH key
        slugged_username = self._add_ssh_key(username, ssh_pubkey)
        
        # Create a unique repo name with timestamp
        timestamp = int(time.time())
        slugged_unit_name = self._slugify(unit_name)
        repo_name = f"{slugged_unit_name}_{timestamp}"
        
        # Add the repo to the config
        self._add_repo_to_config(repo_name, slugged_username)
        
        # Commit and push the changes
        self._run_git_command(["commit", "-m", f"Add user {slugged_username} and repo {repo_name}"])
        self._run_git_command(["push", "origin", "master"])
        
        # Return the remote URL
        return f"{self.gitolite_url}:{repo_name}"


def get_gitolite_service() -> GitoliteService:
    """
    Factory function to create a GitoliteService instance.
    
    This function is used as a FastAPI dependency.
    
    Returns:
        GitoliteService instance
    """
    gitolite_root = os.environ.get("GITOLITE_ROOT", "/path/to/gitolite-admin")
    gitolite_url = os.environ.get("GITOLITE_URL", "gitolite@example.com")
    
    return GitoliteService(gitolite_root, gitolite_url)
