import os

from sqlalchemy import create_engine, Column, Integer, String, Text, Table, inspect, MetaData, Inspector, text, select
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from DataReader.DataRead_file import parse_xml
from Database.structure import SevillaTable, Base
import traceback

engine = create_engine('sqlite:///saensepaard.db')
Session = sessionmaker(bind=engine)
session = Session()


# Initieer de database zonder metadata
def init_db(socketio):
    # Creëer de SevillaTable
    SevillaTable.__table__.create(bind=engine, checkfirst=True)


def make_table(sev_file, socketio, session, sev_index, total_amount_sevs, created_date, data):
    print(f"Begin van data make_table() in repository.py:\n{data}\nEinde van data make_table() in repository.py.")
    print(f"\ndata.keys() = {data.keys()}")
    print(f"\ndata.values() = {data.values()}")

    title = sev_file.filename
    formatted_date = created_date.strftime("%Y%m%d_%H%M")
    table_name = f"{title}_{formatted_date}".replace(' ', '_').replace('.', '_')
    print(f"table_name={table_name}")

    if not data:
        return "Geen gegevens gevonden in het XML-bestand.", 400

    columns = [Column('unique_upload_id', Integer, primary_key=True)]
    columns.extend(Column(key, Text) for key in data.keys())  # Gebruik Text voor grotere tekstkolommen

    print(f"Initial columns={columns}")
    print("Starten met lokale MetaData voor dynamische kolommen...")

    metadata = MetaData()
    engine = create_engine('sqlite:///saensepaard.db')
    dynamic_table = Table(table_name, metadata, *columns, extend_existing=True)

    try:
        metadata.create_all(engine)
        print(f"Tabel '{table_name}' succesvol aangemaakt.")
    except SQLAlchemyError as e:
        print(f"Fout bij het aanmaken van de tabel: {e}")
        print(traceback.format_exc())
        return "Fout bij het aanmaken van de tabel.", 500

    # Verwerk data om ongewenste waarden te verwijderen en speciale tekens te normaliseren
    data = {key: str(value).replace('\\', '/') if isinstance(value, str) else value for key, value in data.items()}

    for key, value in data.items():
        if not isinstance(value, (str, int, float, bytes)):
            print(f"make_table(): waarde van key={key} heeft een niet-ondersteund type: {type(value)}")
            data[key] = str(value)  # Converteer niet-ondersteunde types naar string

    try:
        with engine.connect() as conn:
            print(f"Data om in te voegen met engine.connect(): {data}")

            insert_statement = dynamic_table.insert().values(data)
            print(f"Uitgevoerde query: {insert_statement}")
            print(f"Parameters: {data}")

            conn.execute(insert_statement)
            conn.commit()
            print(f"Gegevens succesvol ingevoegd in de dynamische tabel '{table_name}'.")

            # Bekijk gemaakte dynamic_table in database
            view_table(engine, table_name)

    except SQLAlchemyError as e:
        print(f"Fout bij het invoegen van gegevens: {e}")
        print(traceback.format_exc())
        return "Fout bij het invoegen van gegevens.", 500

    try:
        new_sevilla_table = SevillaTable(
            title=table_name,
            name=title,
            upload_date=created_date
        )
        session.add(new_sevilla_table)
        session.commit()
        print(f"Nieuwe tabel '{table_name}' toegevoegd aan SevillaTable.")
        return f"Tabel '{table_name}' succesvol aangemaakt en gevuld.", 200
    except SQLAlchemyError as e:
        print(f"Fout bij het toevoegen van de tabel aan SevillaTable: {e}")
        print(traceback.format_exc())
        session.rollback()
        return "Fout bij het toevoegen van de tabel aan SevillaTable.", 500


def drop_old_duplicate_table(engine, table_name):
    """Verwijder een oude tabel met dezelfde naam als 'table_name' als deze bestaat."""
    metadata = MetaData()
    metadata.reflect(bind=engine)

    if table_name in metadata.tables:
        table = metadata.tables[table_name]
        try:
            # Verwijder de tabel
            with engine.connect() as conn:
                conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            print(f"Tabel '{table_name}' succesvol verwijderd.")
        except SQLAlchemyError as e:
            print(f"Fout bij het verwijderen van de tabel '{table_name}': {e}")
            return f"Fout bij het verwijderen van de tabel '{table_name}'.", 500
    else:
        print(f"Tabel '{table_name}' bestaat niet.")
        return f"Tabel '{table_name}' bestaat niet.", 404


def delete_old_file(file_path):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Bestand '{file_path}' succesvol verwijderd.")
        else:
            print(f"Bestand '{file_path}' bestaat niet.")
    except Exception as e:
        print(f"Fout bij het verwijderen van bestand '{file_path}': {e}")
        raise


def get_tables(session):
    try:
        # Haal alle SevillaTable records op
        return session.query(SevillaTable).all()
    except SQLAlchemyError as e:
        print(f"Fout bij het ophalen van tabellen: {e}")
        return []


def get_statistics_data(table_name, engine, column_name, query_value):
    metadata = MetaData()
    table = Table(table_name, metadata, autoload_with=engine)

    # Construct a query to search within the specified column
    query = select([table]).where(table.c[column_name].ilike(f'%{query_value}%'))

    with engine.connect() as connection:
        result = connection.execute(query)
        return result.fetchall()


def get_table_data(engine, table_name):
    try:
        with engine.connect() as conn:
            query = text(f'SELECT * FROM {table_name}')
            result = conn.execute(query)
            return result.fetchall()
    except Exception as e:
        print(f"Fout bij het ophalen van gegevens uit de tabel '{table_name}': {e}")
        return None


def view_table(engine, table_name):
    metadata = MetaData()
    dynamic_table = Table(table_name, metadata, autoload_with=engine)

    with engine.connect() as conn:
        query = select(dynamic_table)
        print(f"Executing query: {query}")
        result = conn.execute(query)
        rows = result.fetchall()

        # Print kolomnamen
        column_names = dynamic_table.columns.keys()
        print(f"Kolomnamen dynamic_table volgens view_table: {column_names}")

        # Print gegevens
        print("\nRijen van dynamic_table:")
        for row in rows:
            print(row)
        print("\nEinde rijen van dynamic_table.")


def search_across_tables(engine, column_name, query_value):
    metadata = MetaData()
    metadata.reflect(bind=engine)
    results = []

    # Iterate over all tables in the database
    for table_name, table in metadata.tables.items():
        if column_name in table.c:
            # Construct a query to search within the specified column
            stmt = select(table).where(table.c[column_name].ilike(f'%{query_value}%'))
            with engine.connect() as connection:
                result = connection.execute(stmt)
                rows = result.fetchall()

                # Convert each row to a dictionary using _asdict()
                rows_dicts = [row._asdict() for row in rows]

                if rows_dicts:
                    results.append({
                        'table_name': table_name,
                        'rows': rows_dicts
                    })

    return results


def query_database(table_name):
    try:
        # Haal kolommen op via inspect
        inspector = inspect(session.bind)
        if not inspector.has_table(table_name):
            return None, None

        columns = [column['name'] for column in inspector.get_columns(table_name)]

        # Voer een ruwe SQL-query uit om alle rijen op te halen
        result = session.execute(f"SELECT * FROM {table_name}").fetchall()
        rows = [dict(row) for row in result]

        return rows, columns
    except SQLAlchemyError as e:
        print(f"Fout bij het ophalen van gegevens uit de tabel '{table_name}': {e}")
        return None, None
