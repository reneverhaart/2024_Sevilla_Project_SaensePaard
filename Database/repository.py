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
    table_name = f"{title}_".replace(' ', '_').replace('.', '_')
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

    # Controleer of de tabel bestaat in de metadata
    if table_name in metadata.tables:
        try:
            # Verwijder de tabel
            with engine.connect() as conn:
                conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            print(f"Tabel '{table_name}' succesvol verwijderd.")

            # Controleer opnieuw of de tabel nog steeds bestaat
            insp = inspect(engine)
            if table_name in insp.get_table_names():
                print(f"Waarschuwing: Tabel '{table_name}' bestaat nog steeds in de database.")
            else:
                print(f"Bevestiging: Tabel '{table_name}' is succesvol verwijderd uit de database.")

        except SQLAlchemyError as e:
            print(f"Fout bij het verwijderen van de tabel '{table_name}': {e}")
            return f"Fout bij het verwijderen van de tabel '{table_name}'.", 500
    else:
        print(f"Tabel '{table_name}' bestaat niet.")
        return f"Tabel '{table_name}' bestaat niet.", 404

    return f"Tabel '{table_name}' succesvol verwijderd.", 200


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
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    results = []
    column_variants = [column_name, column_name.upper(), column_name.lower()]

    print(f"Zoeken in kolommen: {column_variants} met waarde: {query_value}")  # Debug output

    for table_name in table_names:
        table = Table(table_name, metadata, autoload_with=engine)
        found_column = None

        # Zoek de kolom in verschillende varianten
        for variant in column_variants:
            if variant in table.c:
                found_column = variant
                break

        if not found_column:
            print(f"Geen van de kolommen {column_variants} gevonden in tabel '{table_name}'")  # Debug output
            continue

        print(f"Gebruik kolom '{found_column}' voor zoekopdracht")  # Debug output

        # Maak een correcte select-query
        query = select(table).where(table.c[found_column].ilike(f'%{query_value}%'))
        print(f"Uitvoeren query: {query}")  # Debug output

        try:
            with engine.connect() as connection:
                result = connection.execute(query)
                rows = result.fetchall()
                if rows:
                    results.append({
                        'table': table_name,
                        'rows': rows
                    })
        except Exception as e:
            print(f"Fout bij uitvoeren van query: {e}")

    print(f"Resultaten gevonden: {results}")  # Debug output
    return results


def delete_file_from_session(sev_file_to_delete):
    print(f"Probeer tabel '{sev_file_to_delete.title}' te verwijderen...")

    # Delete the file in the session
    session.delete(sev_file_to_delete)

    # Save changes for upcoming sessions
    session.commit()

    # Check if table still in query for optional debugging
    rows, columns = query_database(sev_file_to_delete.title, warning=False)

    # Refresh MetaData
    metadata = MetaData()
    metadata.reflect(bind=engine)

    if rows is None and columns is None:
        print(f"Tabel '{sev_file_to_delete.title}' is dus succesvol verwijderd uit de database.")
    else:
        print(f"Waarschuwing: Tabel '{sev_file_to_delete.title}' bestaat nog steeds in de database.")


def query_database(table_name, warning=True):
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
        if warning:
            print(f"Fout bij het ophalen van gegevens uit de tabel '{table_name}': {e}")
        return None, None
