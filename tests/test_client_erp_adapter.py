import json
import pytest
from pathlib import Path
from unittest.mock import mock_open, patch
from adapters.client_erp_adapter import ClientERP


@pytest.fixture
def client_erp():
    """Fixture to create a ClientERP instance"""
    return ClientERP()


@pytest.fixture
def temp_json_dir(tmp_path):
    """Fixture to create a temporary directory with JSON files"""
    json_dir = tmp_path / "json_files"
    json_dir.mkdir()
    
    # Create some test JSON files
    (json_dir / "file1.json").write_text('{"key": "value1"}')
    (json_dir / "file2.json").write_text('{"key": "value2"}')
    (json_dir / "file3.json").write_text('{"key": "value3"}')
    
    # Create a non-JSON file
    (json_dir / "file.txt").write_text("not a json file")
    
    return json_dir


class TestCaptureJsonFilenames:
    """Tests for capture_json_filenames method"""
    
    def test_capture_json_filenames_success(self, client_erp, temp_json_dir):
        """Test successful capture of JSON filenames"""
        result = client_erp.capture_json_filenames(temp_json_dir)
        
        assert len(result) == 3
        assert all(isinstance(path, Path) for path in result)
        assert all(path.suffix == ".json" for path in result)
        assert all(path.name in ["file1.json", "file2.json", "file3.json"] for path in result)
    
    def test_capture_json_filenames_not_a_directory(self, client_erp, tmp_path):
        """Test when path is not a directory"""
        file_path = tmp_path / "not_a_dir.txt"
        file_path.write_text("test")
        
        result = client_erp.capture_json_filenames(file_path)
        
        assert result == []
    
    def test_capture_json_filenames_empty_directory(self, client_erp, tmp_path):
        """Test when directory is empty"""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        result = client_erp.capture_json_filenames(empty_dir)
        
        assert result == []
    
    def test_capture_json_filenames_no_json_files(self, client_erp, tmp_path):
        """Test when directory has no JSON files"""
        no_json_dir = tmp_path / "no_json"
        no_json_dir.mkdir()
        (no_json_dir / "file.txt").write_text("test")
        (no_json_dir / "file.xml").write_text("<xml/>")
        
        result = client_erp.capture_json_filenames(no_json_dir)
        
        assert result == []
    

class TestReadJsonFile:
    """Tests for read_json_file method"""
    
    def test_read_json_file_success(self, client_erp, tmp_path):
        """Test successful JSON file reading"""
        json_file = tmp_path / "test.json"
        test_data = {"orderNo": "12345", "amount": 100.50}
        json_file.write_text(json.dumps(test_data))
        
        result = client_erp.read_json_file(json_file)
        
        assert result == test_data
    
    
    def test_read_json_file_malformed_json(self, client_erp, tmp_path):
        """Test reading malformed JSON"""
        json_file = tmp_path / "malformed.json"
        json_file.write_text('{"key": "value"')  # Missing closing brace
        
        result = client_erp.read_json_file(json_file)
        
        assert result is None
    
    def test_read_json_file_empty_file(self, client_erp, tmp_path):
        """Test reading empty JSON file"""
        json_file = tmp_path / "empty.json"
        json_file.write_text("")
        
        result = client_erp.read_json_file(json_file)
        
        assert result is None
    
    def test_read_json_file_non_existent(self, client_erp, tmp_path):
        """Test reading non-existent file"""
        json_file = tmp_path / "non_existent.json"
        
        with pytest.raises(FileNotFoundError):
            client_erp.read_json_file(json_file)


class TestWriteJsonFile:
    """Tests for write_json_file method"""
    
    def test_write_json_file_success(self, client_erp, tmp_path):
        """Test successful JSON file writing"""
        content = {"orderNo": "12345", "amount": 100.50}
        
        result = client_erp.write_json_file(tmp_path, content)
        
        assert result is True
        written_file = tmp_path / "12345.json"
        assert written_file.exists()
        
        with open(written_file, "r", encoding="utf-8") as f:
            written_content = json.load(f)
        assert written_content == content
    
    
    def test_write_json_file_overwrites_existing(self, client_erp, tmp_path):
        """Test overwriting existing file"""
        order_no = "12345"
        existing_file = tmp_path / f"{order_no}.json"
        existing_file.write_text('{"old": "data"}')
        
        new_content = {"orderNo": order_no, "new": "data"}
        result = client_erp.write_json_file(tmp_path, new_content)
        
        assert result is True
        with open(existing_file, "r", encoding="utf-8") as f:
            written_content = json.load(f)
        assert written_content == new_content
    
    def test_write_json_file_directory_not_exist(self, client_erp, tmp_path):
        """Test writing to non-existent directory"""
        non_existent_dir = tmp_path / "non_existent_dir"
        content = {"orderNo": "12345", "amount": 100.50}
        
        result = client_erp.write_json_file(non_existent_dir, content)
        
        assert result is False
    
    @patch("builtins.open", new_callable=mock_open)
    def test_write_json_file_permission_error(self, mock_file, client_erp, tmp_path):
        """Test when permission is denied"""
        mock_file.side_effect = PermissionError("Permission denied")
        content = {"orderNo": "12345", "amount": 100.50}
        
        result = client_erp.write_json_file(tmp_path, content)
        
        assert result is False
