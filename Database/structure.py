from sqlalchemy import (Column, Integer, String, ForeignKey, Date, Double, TEXT)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

# Alle klassen hier nog veranderen op basis van Sevilla dump documenten

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


class Page(Base):
    __tablename__ = 'Page'

    id = Column(Integer, primary_key=True)
    text = Column(TEXT)
    page_number = Column(Integer)
    complexity_score = Column(Integer)
    magazine_id = Column(Integer, ForeignKey('Magazine.id'))

    def __str__(self):
        return ""


class WordObject(Base):
    __tablename__ = 'Wordlist'

    id = Column(Integer, primary_key=True)
    word = Column(String)
    type = Column(String)  # reductionistic = 1, complex = 2, antonym = 3
    weight = Column(Integer)
