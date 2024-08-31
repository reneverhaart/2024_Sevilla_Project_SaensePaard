from sqlalchemy import (Column, Integer, String, DateTime, Text)  # , ForeignKey, Date, Double)
from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import relationship

Base = declarative_base()


# Alle klassen hier nog veranderen op basis van Sevilla dump documenten

# SQLAlchemy model for the new table
class SevillaTable(Base):
    __tablename__ = 'SevillaTable'
    id = Column(Integer, primary_key=True)
    title = Column(String)
    name = Column(String)
    upload_date = Column(DateTime)
    # pages = relationship("Page", backref="Magazine")

    def __str__(self):
        return f"Table(id={self.id}, title={self.title}, name={self.name}, upload_date={self.upload_date})"

"""
class Magazine(Base):
    __tablename__ = 'Magazine'

    id = Column(Integer, primary_key=True)
    publication_date = Column(Date)
    upload_date = Column(Date)
    title = Column(String(255))
    hashvalue = Column(String(64))
    complexity_score = Column(Double)
    reductionistic_score = Column(Double)
    pages = relationship("Page", backref="Magazine")

    def __str__(self):
        return ""
"""
