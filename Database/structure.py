from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class SevillaTable(Base):
    __tablename__ = 'SevillaTable'
    id = Column(Integer, primary_key=True)
    title = Column(String)
    name = Column(String)
    upload_date = Column(DateTime)

    def __str__(self):
        return f"Table(id={self.id}, title={self.title}, name={self.name}, upload_date={self.upload_date})"
