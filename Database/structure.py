from sqlalchemy import (Column, Integer, String, Text)  # , ForeignKey, Date, Double)
from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import relationship

Base = declarative_base()


# Alle klassen hier nog veranderen op basis van Sevilla dump documenten

# SQLAlchemy model for the new table
class XMLData(Base):
    __tablename__ = 'xml_data'
    id = Column(Integer, primary_key=True)
    field1 = Column(String, nullable=False)
    field2 = Column(Text)
    # pages = relationship("Page", backref="Magazine")

    # def __str__(self):
    #    return ""


"""
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
"""
