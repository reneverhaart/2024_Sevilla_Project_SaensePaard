from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class SevillaTable(Base):
    __tablename__ = 'SevillaTable'
    id = Column(Integer, primary_key=True)
    title = Column(String)
    name = Column(String)
    upload_date = Column(DateTime)
    created_date = Column(DateTime)

    rounds = relationship("Round", back_populates="tournament", cascade="all, delete-orphan")
    players = relationship("Player", back_populates="tournament", cascade="all, delete-orphan")


class Round(Base):
    __tablename__ = 'rounds'
    id = Column(Integer, primary_key=True)
    sevilla_id = Column(Integer, ForeignKey('SevillaTable.id'), nullable=False)
    round_number = Column(Integer)
    date = Column(DateTime)

    tournament = relationship("SevillaTable", back_populates="rounds")
    games = relationship("Game", back_populates="round", cascade="all, delete-orphan")
    absences = relationship("Absence", back_populates="round", cascade="all, delete-orphan")

class Game(Base):
    __tablename__ = 'games'
    id = Column(Integer, primary_key=True)
    sevilla_id = Column(Integer, ForeignKey('SevillaTable.id'), nullable=False)
    round_id = Column(Integer, ForeignKey('rounds.id'), nullable=False)
    white_player = Column(String)
    black_player = Column(String)
    result = Column(String)

    round = relationship("Round", back_populates="games")


class Player(Base):
    __tablename__ = 'players'
    id = Column(Integer, primary_key=True)           # dit is speler-ID uit XML
    sevilla_id = Column(Integer, ForeignKey('SevillaTable.id'), nullable=False)
    first_name = Column(String)
    last_name = Column(String)

    tournament = relationship("SevillaTable", back_populates="players")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class Absence(Base):
    __tablename__ = 'absences'
    id = Column(Integer, primary_key=True)
    sevilla_id = Column(Integer, ForeignKey('SevillaTable.id'), nullable=False)
    round_id = Column(Integer, ForeignKey('rounds.id'), nullable=False)
    player_name = Column(String)

    round = relationship("Round", back_populates="absences")