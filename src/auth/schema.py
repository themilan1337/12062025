from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    age = Column(Integer)
    name = Column(String)
    messages = relationship("Message", back_populates="user")
    chat_participations = relationship(
        "ChatParticipant", back_populates="user"
    )

    @property
    def username(self):
        return self.name or self.email.split('@')[0]
