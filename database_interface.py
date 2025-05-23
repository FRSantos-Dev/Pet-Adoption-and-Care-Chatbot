from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, TypedDict, Union
from datetime import datetime

class UserInfo(TypedDict):
    id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]

class InterviewInfo(TypedDict):
    id: int
    interviewee_id: int
    animal_type: str
    animal_id: Optional[int]
    status: str
    created_at: datetime
    completed_at: Optional[datetime]

class FileInfo(TypedDict):
    id: int
    interview_id: int
    file_type: str
    file_path: str
    created_at: datetime

class InterviewResult(TypedDict):
    interview: InterviewInfo
    answers: Dict[str, str]
    files: List[FileInfo]

class DatabaseInterface(ABC):
    """Interface for database operations in the pet adoption system."""
    
    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the database.
        
        Raises:
            Exception: If connection fails.
        """
        pass

    @abstractmethod
    def create_tables(self) -> None:
        """Create necessary tables if they don't exist.
        
        Raises:
            Exception: If table creation fails.
        """
        pass

    @abstractmethod
    def save_interview(self, user_info: UserInfo, animal_type: str, 
                      animal_id: Optional[int], answers: Dict[str, str], 
                      pdf_path: str, image_paths: List[str]) -> int:
        pass

    @abstractmethod
    def get_interview(self, interview_id: int) -> Optional[InterviewResult]:
        pass

    @abstractmethod
    def get_interviews_by_user(self, telegram_id: int) -> List[InterviewInfo]:
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the database connection."""
        pass 