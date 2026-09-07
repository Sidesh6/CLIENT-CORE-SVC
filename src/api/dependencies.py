from collections.abc import Generator
from fastapi import Depends
from sqlalchemy.orm import Session
from src.database.session import get_db

DbSession = Generator[Session, None, None]
