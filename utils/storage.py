import os
from pathlib import Path
from datetime import datetime
import shutil

class LocalStorage:
    def __init__(self):
        self.upload_dir = Path("uploads")
        self.upload_dir.mkdir(exist_ok=True)

    def save_file(self, file, filename: str) -> str:
        """
        Save file to local storage and return the file path
        """
        # Create date-based directory structure
        date_path = datetime.now().strftime("%Y/%m/%d")
        full_path = self.upload_dir / date_path
        full_path.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        timestamp = datetime.now().strftime("%H%M%S")
        safe_filename = f"{timestamp}_{filename}"
        file_path = full_path / safe_filename

        # Save the file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return str(file_path)

    def get_file_path(self, path: str) -> Path:
        """Get full path for a file"""
        return Path(path)

    def delete_file(self, path: str) -> bool:
        """Delete file from storage"""
        try:
            Path(path).unlink()
            return True
        except FileNotFoundError:
            return False 