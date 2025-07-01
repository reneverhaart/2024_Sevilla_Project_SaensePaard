import os
import logging
import re

from sqlalchemy import (
    create_engine, Column, Integer, Text, MetaData,
    Table, inspect, select, text, func
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, scoped_session
from Database.structure import SevillaTable, Base, Round, Game, Absence, Player
from DataReader.DataRead_file import parse_xml, parse_date_safe

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Engine & session factory
ENGINE_URL = 'sqlite:///saensepaard.db'
engine = create_engine(ENGINE_URL, echo=False)
SessionFactory = sessionmaker(bind=engine)
Session = scoped_session(SessionFactory)


# Initialize DB and create SevillaTable
def init_db():
    Base.metadata.create_all(engine)
    logger.info("Database initialized and tables created.")


# Drop table if exists
def drop_table(table_name: str):
    metadata = MetaData()
    metadata.reflect(bind=engine)
    if table_name in metadata.tables:
        with engine.begin() as conn:
            conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
        logger.info(f"Dropped existing table: {table_name}")
    else:
        logger.debug(f"Table '{table_name}' does not exist.")


def safe_table_name(name: str) -> str:
    # Vervang alles wat geen letter, cijfer of underscore is door underscore
    safe_name = re.sub(r'[^a-zA-Z0-9_]+', '_', name)
    # Verwijder dubbele underscores
    safe_name = re.sub(r'_+', '_', safe_name)
    # Verwijder underscore aan het begin en eind (optioneel)
    safe_name = safe_name.strip('_')
    return safe_name


# Create and populate a dynamic table from sev data
def make_table(sev_file, sev_index: int, total_amount_sevs: int, upload_date, created_date_xml, data: dict):
    if not data:
        return "Geen gegevens gevonden in het XML-bestand.", 400

    title = sev_file.filename

    # In plaats van dynamische tabel aan te maken, alleen metadata opslaan
    session = Session()

    print(f"\nmake_table data van bestand '{title}': \n{data}\n")
    try:
        # Eerst metadata recorden in SevillaTable
        record = SevillaTable(title=title, name=title,
                              upload_date=upload_date, created_date=created_date_xml)
        session.add(record)
        session.commit()
        sevilla_id = record.id  # Primary key van dit toernooi

        # Check op "Jeugd" in titel (case-insensitive)
        #=>Senioren wordt IDs 10000+
        #=>Jeugd wordt IDs 0-9999
        jeugd_offset = 10000 if not "jeugd" in title.lower() else 0

        players_data = data.get('COMP', {}).get('players', [])
        for p in players_data:
            original_id = p.get('ID')
            if original_id is None or not original_id.isdigit():
                continue  # of afhandelen indien nodig

            player_id = int(original_id) + jeugd_offset
            player_obj = Player(
                id=player_id,
                sevilla_id=sevilla_id,
                first_name=p.get('FIRST', ''),
                last_name=p.get('LAST', '')
            )
            exists = session.query(Player).filter_by(id=player_id).first()
            if not exists: # Om "UNIQUE constraint failed"-error te voorkomen
                session.add(player_obj)

        rounds_data = data.get('COMP', {}).get('rounds', [])
        print(f"Aantal rondes: {len(rounds_data)}")
        for round_dict in rounds_data:
            print(f"Ronde dict keys: {list(round_dict.keys())}")

            round_num = int(round_dict.get('ID', 0))
            date_str = round_dict.get('DATE')
            print(f"\ndate_str:\n{date_str}\n")
            round_date = parse_date_safe(date_str) if date_str else None
            print(f"\nround_date:\n{round_date}\n")

            round_obj = Round(sevilla_id=sevilla_id, round_number=round_num, date=round_date)
            session.add(round_obj)
            session.flush()

            games_data = round_dict.get('games', [])
            print(f"Aantal games in ronde {round_num}: {len(games_data)}")
            for game_dict in games_data:
                print(f"Game dict keys: {list(game_dict.keys())}")
                white = game_dict.get('WHITE')
                black = game_dict.get('BLACK')
                result = game_dict.get('RES')
                game_obj = Game(sevilla_id=sevilla_id, round_id=round_obj.id,
                                white_player=white, black_player=black, result=result)
                session.add(game_obj)

            absences_data = round_dict.get('absences', [])
            print(f"Aantal afwezigen in ronde {round_num}: {len(absences_data)}")
            for absence_dict in absences_data:
                print(f"Absence dict keys: {list(absence_dict.keys())}")
                player_name = absence_dict.get('PLAYER')
                absence_obj = Absence(sevilla_id=sevilla_id, round_id=round_obj.id,
                                      player_name=player_name)
                session.add(absence_obj)

        session.commit()
        return f"Gegevens uit '{title}' succesvol aangemaakt en gevuld.", 200

    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Fout bij het invoegen van gegevens: {e}")
        return "Fout bij het invoegen van gegevens.", 500
    finally:
        session.close()


# Delete associated file from disk
def delete_old_file(file_path: str):
    try:
        os.remove(file_path)
        logger.info(f"Deleted file: {file_path}")
    except FileNotFoundError:
        logger.warning(f"File '{file_path}' not found.")
    except Exception as e:
        logger.error(f"Error deleting file '{file_path}': {e}")
        raise

# Fetch all SevillaTable entries
def get_tables():
    session = Session()
    try:
        return session.query(SevillaTable).all()
    finally:
        session.close()

# List all table names in DB
def get_table_names():
    inspector = inspect(engine)
    return inspector.get_table_names()

# Fetch all rows from a dynamic table
def get_table_data(table_name: str):
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f'SELECT * FROM "{table_name}"'))
            return result.fetchall()
    except SQLAlchemyError as e:
        logger.error(f"Error fetching data from '{table_name}': {e}")
        return []

# Search a column across all tables
def search_across_tables(column_name: str, query_value: str):
    results = []
    for table_name in get_table_names():
        metadata = MetaData()
        metadata.reflect(bind=engine)
        table = Table(table_name, metadata, autoload_with=engine)
        col = next((c for c in table.c if c.name.lower() == column_name.lower()), None)
        if not col:
            continue
        stmt = select(table).where(col.ilike(f'%{query_value}%'))
        with engine.connect() as conn:
            rows = conn.execute(stmt).fetchall()
            if rows:
                results.append({'table': table_name, 'rows': rows})
    return results

# Recursively search nested data
def specific_search_data(data, key_to_find: str):
    if isinstance(data, dict):
        if key_to_find in data:
            return data[key_to_find]
        for value in data.values():
            found = specific_search_data(value, key_to_find)
            if found is not None:
                return found
    elif isinstance(data, list):
        for item in data:
            found = specific_search_data(item, key_to_find)
            if found is not None:
                return found
    return None

# Search term in all tables
def specific_search_data_in_all_tables(search_term: str):
    results = []
    for table_name in get_table_names():
        rows = get_table_data(table_name)
        found = specific_search_data(rows, search_term)
        if found is not None:
            results.append({'table': table_name, 'result': found})
    return results

# Get statistics for a column (value counts), optionally filtered by a query
def get_statistics_data(engine, table_name: str, column_name: str, query_value: str = None):
    session = Session()
    metadata = MetaData()
    metadata.reflect(bind=engine)
    table = Table(table_name, metadata, autoload_with=engine)
    stmt = select(table.c[column_name], func.count().label('count')).group_by(table.c[column_name])
    if query_value:
        stmt = stmt.where(table.c[column_name].ilike(f'%{query_value}%'))
    try:
        result = session.execute(stmt).fetchall()
        return [{'value': r[0], 'count': r[1]} for r in result]
    finally:
        session.close()

# Provide search suggestions based on existing table data
def get_search_suggestions(engine, table_name: str, search_term: str, limit: int = 10):
    suggestions = set()
    metadata = MetaData()
    metadata.reflect(bind=engine)
    table = Table(table_name, metadata, autoload_with=engine)
    with engine.connect() as conn:
        for col in table.c:
            # only text-like columns
            if hasattr(col.type, 'length') or isinstance(col.type, Text):
                stmt = select(col).where(col.ilike(f'%{search_term}%')).limit(limit)
                for val, in conn.execute(stmt).fetchall():
                    if isinstance(val, str) and search_term.lower() in val.lower():
                        suggestions.add(val)
                    if len(suggestions) >= limit:
                        break
            if len(suggestions) >= limit:
                break
    return list(suggestions)
