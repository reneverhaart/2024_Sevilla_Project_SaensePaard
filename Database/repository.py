import os

from sqlalchemy import create_engine, Column, Integer, String, Text, Table, inspect, MetaData, Inspector
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

    # Als data een enkele dictionary is
    if isinstance(data, dict):
        data = [data]

    if not isinstance(data, list) or not all(isinstance(record, dict) for record in data):
        return "Onverwacht formaat van de gegevens. Verwacht een lijst van dictionaries.", 400

    columns = [Column('id_tabelnummer', Integer, primary_key=True)]
    column_types = {}
    print(f"columns={columns}")

    # Verkrijg kolomnamen en types op basis van een voorbeeld record
    if data:
        example_record = data[0]
        for column_name in example_record.keys():
            column_name = column_name.strip().upper()
            value = example_record.get(column_name)

            # Bepaal het type van de kolom
            if isinstance(value, str):
                column_types[column_name] = Text
            elif isinstance(value, int):
                column_types[column_name] = Integer
            else:
                column_types[column_name] = String

    print("Starten met lokale MetaData voor dynamische kolommen...")
    metadata = MetaData()
    columns.extend(Column(name, type_) for name, type_ in column_types.items())
    engine = create_engine('sqlite:///saensepaard.db')
    dynamic_table = Table(table_name, metadata, *columns)
    print(f"Geëxtraheerde kolommen: {columns}")
    print(f"Geëxtraheerde kolomtypes: {column_types}")

    try:
        metadata.create_all(engine)
        print(f"Tabel '{table_name}' succesvol aangemaakt.")
    except SQLAlchemyError as e:
        print(f"Fout bij het aanmaken van de tabel: {e}")
        print(traceback.format_exc())
        return "Fout bij het aanmaken van de tabel.", 500

    try:
        values_list = []
        for record in data:
            if isinstance(record, dict):
                values = {col: record.get(col, None) for col in column_types.keys()}
                print(f"Record values: {values}")
                values_list.append(values)
            else:
                print(f"Waarschuwing: Onverwacht recordtype: {type(record)}. Record: {record}")

        with engine.connect() as conn:
            conn.execute(dynamic_table.insert(), values_list)
            print(f"Gegevens succesvol toegevoegd aan de tabel '{table_name}'.")
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
