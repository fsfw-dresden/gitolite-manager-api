import os
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from services.gitolite_service import GitoliteService

class TestGitoliteService:
    @pytest.fixture
    def mock_gitolite_root(self):
        """Create a temporary directory structure mimicking gitolite-admin."""
        with tempfile.TemporaryDirectory() as temp_dir:
            gitolite_root = Path(temp_dir)
            
            # Create keydir
            keydir = gitolite_root / "keydir"
            keydir.mkdir()
            
            # Create conf directory and gitolite.conf
            conf_dir = gitolite_root / "conf"
            conf_dir.mkdir()
            conf_file = conf_dir / "gitolite.conf"
            conf_file.write_text("# Gitolite configuration\n")
            
            yield gitolite_root
    
    @pytest.fixture
    def gitolite_service(self, mock_gitolite_root):
        """Create a GitoliteService instance with the mock gitolite root."""
        return GitoliteService(
            gitolite_root=str(mock_gitolite_root),
            gitolite_url="gitolite@example.com"
        )
    
    def test_slugify(self, gitolite_service):
        """Test the _slugify method."""
        assert gitolite_service._slugify("Test User") == "test_user"
        assert gitolite_service._slugify("Test-User!@#") == "test-user"
        assert gitolite_service._slugify("  spaces  ") == "spaces"
    
    def test_key_exists(self, gitolite_service, mock_gitolite_root):
        """Test the _key_exists method."""
        # Create a test key file
        test_key_path = mock_gitolite_root / "keydir" / "test_user.pub"
        test_key_path.write_text("ssh-rsa AAAAB3NzaC1yc2E... test@example.com\n")
        
        assert gitolite_service._key_exists("test_user") is True
        assert gitolite_service._key_exists("nonexistent_user") is False
    
    @patch('services.gitolite_service.GitoliteService._run_git_command')
    def test_add_ssh_key(self, mock_run_git, gitolite_service, mock_gitolite_root):
        """Test the _add_ssh_key method."""
        mock_run_git.return_value = ""
        
        # Test adding a new key
        username = "new_user"
        ssh_pubkey = "ssh-rsa AAAAB3NzaC1yc2E... new@example.com"
        
        result = gitolite_service._add_ssh_key(username, ssh_pubkey)
        assert result == "new_user"
        
        # Verify the key was written
        key_path = mock_gitolite_root / "keydir" / "new_user.pub"
        assert key_path.exists()
        assert key_path.read_text().strip() == ssh_pubkey
        
        # Verify git add was called
        mock_run_git.assert_called_once_with(["add", "keydir/new_user.pub"])
        
        # Test adding an existing key
        mock_run_git.reset_mock()
        with pytest.raises(ValueError, match="SSH key for user 'new_user' already exists"):
            gitolite_service._add_ssh_key(username, ssh_pubkey)
    
    @patch('services.gitolite_service.GitoliteService._run_git_command')
    def test_add_repo_to_config(self, mock_run_git, gitolite_service, mock_gitolite_root):
        """Test the _add_repo_to_config method."""
        mock_run_git.return_value = ""
        
        repo_name = "test_repo_123"
        username = "test_user"
        
        gitolite_service._add_repo_to_config(repo_name, username)
        
        # Verify the config was updated
        config_path = mock_gitolite_root / "conf" / "gitolite.conf"
        config_content = config_path.read_text()
        
        assert f"repo {repo_name}" in config_content
        assert f"RW+     =   {username}" in config_content
        
        # Verify git add was called
        mock_run_git.assert_called_once_with(["add", "conf/gitolite.conf"])
    
    @patch('services.gitolite_service.GitoliteService._run_git_command')
    @patch('services.gitolite_service.GitoliteService._add_ssh_key')
    @patch('services.gitolite_service.GitoliteService._add_repo_to_config')
    @patch('time.time')
    def test_create_repo_with_key(self, mock_time, mock_add_repo, mock_add_key, mock_run_git, gitolite_service):
        """Test the create_repo_with_key method."""
        # Setup mocks
        mock_time.return_value = 1234567890
        mock_add_key.return_value = "test_user"
        mock_run_git.return_value = ""
        
        ssh_pubkey = "ssh-rsa AAAAB3NzaC1yc2E... test@example.com"
        unit_name = "Test Unit"
        username = "Test User"
        
        result = gitolite_service.create_repo_with_key(ssh_pubkey, unit_name, username)
        
        # Verify the result
        assert result == "gitolite@example.com:test_unit_1234567890"
        
        # Verify the methods were called
        mock_add_key.assert_called_once_with(username, ssh_pubkey)
        mock_add_repo.assert_called_once_with("test_unit_1234567890", "test_user")
        
        # Verify git commands were called
        assert mock_run_git.call_count == 2
        mock_run_git.assert_any_call(["commit", "-m", "Add user test_user and repo test_unit_1234567890"])
        mock_run_git.assert_any_call(["push", "origin", "master"])
