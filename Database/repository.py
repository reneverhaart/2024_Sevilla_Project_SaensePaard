import os
from datetime import datetime
from Database.structure import SevillaTable, Base
from DataReader.DataRead_file import xml_to_sql, emit_progress_update
from sqlalchemy import create_engine, Column, Integer, String, Text, MetaData, Table, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
import traceback

engine = create_engine('sqlite:///saensepaard.db')
Session = sessionmaker(bind=engine)
session = Session()
metadata = MetaData()  # Keeps SQLite table definitions
metadata.reflect(bind=engine)


def init_db(socketio):
    Base.metadata.create_all(engine)

    # Next code useable for loading initial databases
    xml_file_path = 'data/initial_database.json'
    if os.path.isfile(xml_file_path):
        with open(xml_file_path, 'r') as file:
            xml_to_sql(xml_file_path, socketio, session)

        # for data_ in data.get("words_data", []):
        #    word = WordObject(word=word_data["word"], type=word_data["type"], weight=word_data["weight"])
        #    session.add(word)

        session.commit()
    else:
        print(f"xml_file_path='{xml_file_path}' bestaat niet. Initialisatie wordt overgeslagen.")


def make_table(sev_file, socketio, session, sev_index, total_amount_sevs, xml_columns, created_date):
    # Voorbeeld van hoe je kolomnamen en datum kunt verkrijgen uit sev_file
    title = sev_file.filename  # Voorbeeld titel
    formatted_date = created_date.strftime("%Y%m%d_%H%M")
    table_name = f"{title}_{formatted_date}".replace(' ', '_').replace('.', '_')

    # Maak een MetaData object aan zonder bind
    metadata = MetaData()

    # Define columns
    columns = [Column('ID', Integer, primary_key=True)] + [Column(column, Text) for column in xml_columns]

    # Definieer de tabel
    new_table = Table(table_name, metadata, *columns)

    # Verkrijg de engine uit de session
    engine = session.bind

    # Controleer of de tabel al bestaat
    if engine.dialect.has_table(engine, table_name):
        print(f"Tabel '{table_name}' bestaat al.")
        return f"Tabel '{table_name}' bestaat al."

    try:
        # Maak de nieuwe tabel aan
        metadata.create_all(bind=engine)
        print(f"Database tabel '{table_name}' is aangemaakt.")

        # Voeg tabelinformatie toe aan de database
        new_sevilla_table = SevillaTable(
            title=table_name,
            name=title,
            upload_date=created_date
        )

        session.add(new_sevilla_table)
        session.commit()

        return f"Tabel '{table_name}' succesvol aangemaakt."

    except IntegrityError as e:
        session.rollback()
        print(f"Fout bij het aanmaken van de tabel: {str(e)}")
        return f"Fout bij het aanmaken van de tabel '{table_name}'."

    except Exception as e:
        session.rollback()
        print(f"Onverwachte fout: {str(e)}")
        return f"Onverwachte fout bij het aanmaken van de tabel '{table_name}'."


def get_tables(session):
    try:
        # Query all tables from the database
        tables = session.query(SevillaTable).all()
        return tables
    except Exception as e:
        # Print the stack trace
        tb_str = traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__)
        print("".join(tb_str))
        session.rollback()
        return []


def get_data_from_table(table_name, session):
    # Dynamically get a table from the metadata
    table = metadata.tables.get(table_name)
    if table is None:
        print(f"Tabel '{table_name}' bestaat niet.")
        return False

    try:
        # Query all data from the table
        query = session.query(table)
        return query.all()
    except Exception as e:
        print(f"Fout bij verkrijgen data tabel='{table_name}': {e}")
        session.rollback()
        return False


def query_database(table_name):
    table = Table(table_name, metadata, autoload_with=engine)
    with engine.connect() as connection:
        try:
            query = table.select()
            result = connection.execute(query)
            rows = result.fetchall()
            columns = result.keys()
            if not rows:
                print(f"Geen gegevens gevonden in de tabel '{table_name}'.")

                # Debugging
                print(f"Columns: {columns}")
                print(f"Rows: {rows}")
            return columns, rows
        except Exception as e:
            print(f"Fout bij uitvoeren van query op tabel '{table_name}': {e}")
            raise


def insert_data(table_name, data):
    from sqlalchemy import create_engine, Table
    engine = create_engine('sqlite:///your_database.db')
    metadata = MetaData()

    table = Table(table_name, metadata, autoload_with=engine)
    with engine.connect() as connection:
        for item in data:
            connection.execute(table.insert().values(item))


def drop_old_duplicate_table(table_name):
    # Zorg ervoor dat de metadata is gereflecteerd
    metadata.reflect(bind=engine)

    # Controleer of de tabel bestaat in de database
    inspector = inspect(engine)
    if table_name in inspector.get_table_names():
        try:
            # Verwijder de tabel uit de metadata en dan uit de database
            table = metadata.tables.get(table_name)
            if table:
                table.drop(bind=engine)
                print(f"Tabel '{table_name}' succesvol verwijderd.")
            else:
                print(f"Tabel '{table_name}' is niet gevonden in de metadata.")
        except Exception as e:
            print(f"Fout bij verwijderen van tabel '{table_name}': {e}")
    else:
        print(f"Tabel '{table_name}' bestaat niet in de database.")


"""
def post_magazine(magazine, session):
    try:
        existing_magazine = session.query(Magazine).filter_by(title=magazine.title).first()

        if existing_magazine:
            existing_magazine.publication_date = magazine.publication_date
            existing_magazine.upload_date = magazine.upload_date
            existing_magazine.title = magazine.title
            existing_magazine.complexity_score = magazine.complexity_score
            existing_magazine.reductionistic_score = magazine.reductionistic_score
            session.commit()
            return existing_magazine
        else:
            # Add new page
            session.add(magazine)
            session.commit()
            return magazine
    except Exception as e:
        print(f"Error occurred: {e}")
        session.rollback()  # Roll back changes in case of an error
        return False


def post_page(page, session):
    try:
        existing_page = get_page_by_magazine_id_and_page_number(page.magazine_id, page.page_number, session)

        if existing_page:
            existing_page.text = page.text
            existing_page.complexity_score = page.complexity_score
            session.commit()
            return existing_page
        else:
            # Add new page
            session.add(page)
            session.commit()
            return page
    except Exception as e:
        print(f"Error occurred: {e}")
        session.rollback()  # Roll back changes in case of an error
        return False


def get_magazines(session):
    try:
        all_magazines = session.query(Magazine).all()
        return all_magazines
    except Exception as e:
        print(f"Error occurred: {e}")
        session.rollback()
        return False


def get_magazine_by_id(magazine_id, session):
    try:
        magazine = session.query(Magazine).filter(Magazine.id == magazine_id).first()
        return magazine
    except Exception as e:
        print(f"Error occurred: {e}")
        return None


def get_pages_by_magazine_id(magazine_id, session):
    try:
        pages = session.query(Page).filter(Page.magazine_id == magazine_id).all()
        return pages
    except Exception as e:
        print(f"Error occurred: {e}")
        return None


def get_page_by_magazine_id_and_page_number(magazine_id, page_number, session):
    try:
        page = session.query(Page).filter(Page.magazine_id == magazine_id, Page.page_number == page_number).first()
        return page
    except Exception as e:
        print(f"Error occurred: {e}")
        return None


def delete_page(magazine_id, page_number, session):
    try:
        page = session.query(Page).filter(Page.magazine_id == magazine_id, Page.page_number == page_number).first()
        if page:
            session.delete(page)
            session.commit()
            return True
        else:
            return False
    except Exception as e:
        print(f"Error occurred: {e}")
        session.rollback()
        return False


def delete_magazine_by_magazine_id(magazine_id, session):
    try:
        magazine = session.query(Magazine).filter(Magazine.id == magazine_id).first()
        if magazine:
            # Delete associated pages aswell
            session.query(Page).filter(Page.magazine_id == magazine_id).delete()
            session.delete(magazine)

            session.commit()
            return True
        else:
            return False
    except Exception as e:
        print(f"Error occurred: {e}")
        session.rollback()
        return False


def add_word_object_wordlist(word_object, session):
    try:
        existing_word_object = session.query(WordObject).filter(WordObject.word == word_object.word,
                                                                WordObject.type == word_object.type).first()
        if existing_word_object:
            existing_word_object.weight = word_object.weight
            session.commit()
            return True
        else:
            session.add(word_object)
            session.commit()
            return True
    except Exception as e:
        print(f"Error occurred: {e}")
        session.rollback()
        return False


def get_word_objects_by_type_wordlist(type, session):
    try:
        words_objects = session.query(WordObject).filter(WordObject.type == type).all()
        return words_objects
    except Exception as e:
        print(f"Error occurred: {e}")
        session.rollback()
        return False


def delete_word_with_type_wordlist(word, type, session):
    try:
        word_object = session.query(WordObject).filter(WordObject.word == word, WordObject.type == type).first()
        if word_object:
            session.delete(word_object)
            session.commit()
            return True
        else:
            return False
    except Exception as e:
        print(f"Error occurred: {e}")
        session.rollback()
        return False
"""
