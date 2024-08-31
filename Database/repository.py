from Database.structure import
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import json

engine = create_engine('sqlite:///saensepaard.db')
Session = sessionmaker(bind=engine)
session = Session()


def init_db():
    Base.metadata.create_all(engine)

    # Next code useable for loading initial databases
    with open('data/initial_database.json', 'r') as file:
        data = json.load(file)

    for word_data in data.get("words_data", []):
        word = WordObject(word=word_data["word"], type=word_data["type"], weight=word_data["weight"])
        session.add(word)

    session.commit()


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
