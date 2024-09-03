import os
import subprocess
import sys
import traceback

from sqlalchemy import MetaData, Table, inspect


# Function to download missing packages, needs to be at start of code:
def install_packages():
    try:
        # Try Pip to install packages
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
    except subprocess.CalledProcessError as e:
        print(f"Fout bij het installeren van packages: {e}")
        sys.exit(1)


# Call function for downloading missing packages
install_packages()

# Flask related imports
from flask import Flask, render_template, request
from flask_socketio import SocketIO

# Repository related imports
from Database.repository import init_db, session, make_table, drop_old_duplicate_table, delete_old_file, get_tables, \
    query_database, engine, delete_file_from_session
from Database.structure import SevillaTable

# Data-reading related imports
from DataReader.DataRead_file import emit_progress_update, parse_xml

# Flask app configuration settings
app = Flask(__name__)
app.config['DATABASE'] = './saensepaard.db'
app.config['TEMPLATES_AUTO_RELOAD'] = True
socketio = SocketIO(app)

# Only initialize a new database if there is no database present
if not os.path.isfile(app.config['DATABASE']):
    init_db(socketio)  # repository

# Uploadfolder needs to be connected to Data
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'Data')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Uploadfolder must exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

metadata = MetaData()
metadata.clear()


### STARTING APP ROUTES ###


@app.route("/")
def home():
    return render_template('home.html')


@app.route("/upload", methods=["POST", "GET"])
def upload():
    if request.method == "POST":
        # Zorg ervoor dat de bestanden zijn geüpload
        if 'sevFile' not in request.files:
            return 'No file part', 400

        sev_files = request.files.getlist('sevFile')

        if not sev_files:
            return 'No selected file', 400

        emit_progress_update(socketio, 'Sevilla bestanden verwerken naar database...', 0)
        total_amount_sevs = len(sev_files)

        feedback = None  # Voor het opslaan van feedback van make_table

        # Verwerk elk bestand afzonderlijk
        for sev_index, sev_file in enumerate(sev_files):
            if sev_file.filename != '':
                # Sla het bestand op in de Data map
                sev_file_path = os.path.join(app.config['UPLOAD_FOLDER'], sev_file.filename)
                sev_file.save(sev_file_path)

                # Parse de XML om de benodigde data te verkrijgen
                title, created_date, data = parse_xml(sev_file_path)

                if not data:
                    return "Geen gegevens gevonden in het XML-bestand.", 400

                # Maak de tabel aan met de benodigde argumenten
                feedback, status_code = make_table(
                    sev_file=sev_file,
                    socketio=socketio,
                    session=session,
                    created_date=created_date,
                    sev_index=sev_index + 1,  # Geef de huidige index door
                    total_amount_sevs=total_amount_sevs,
                    data=data
                )
                if status_code != 200:
                    return feedback, status_code

        # Verkrijg de tabelinformatie na verwerking van bestanden
        all_sevs = list(get_tables(session))[::-1]

        emit_progress_update(socketio, 'Verwerking voltooid!', 100)
        return render_template('upload.html', feedback=feedback, sevs=all_sevs)

    else:
        all_sevs = list(get_tables(session))[::-1]
        return render_template('upload.html', sevs=all_sevs)


@app.route("/upload/delete", methods=['POST'])
def delete_old_sev_file():
    sev_id = request.form.get('delete_sev_id')

    if sev_id:
        try:
            # Fetch the sev_file by ID
            sev_file_to_delete = session.query(SevillaTable).get(sev_id)

            if sev_file_to_delete:
                # Bouw de tabelnaam op basis van de title en upload_date
                table_name = f"{sev_file_to_delete.title}_{sev_file_to_delete.upload_date.strftime('%Y%m%d_%H%M')}".replace(
                    ' ', '_').replace('.', '_')

                # Verkrijg de engine uit de session
                engine = session.bind

                # Verwijder de oude tabel
                drop_old_duplicate_table(engine, table_name)

                # Verwijder het record uit de database
                delete_file_from_session(sev_file_to_delete)

                feedback = 'Sev file succesvol verwijderd.'
            else:
                feedback = 'Sev file kan niet verwijderd worden, het is niet gevonden!'
        except Exception as e:
            session.rollback()
            print(f"Error occurred while deleting sev file: {e}")
            feedback = "Er is een fout opgetreden bij het verwijderen van het sev-bestand."
    else:
        feedback = "Geen Sev ID opgegeven."

    # Verkrijg alle Sevilla bestanden na verwijdering
    all_sevs = list(get_tables(session))[::-1]
    return render_template('upload.html', feedback=feedback, sevs=all_sevs)


def flatten_data(data, parent_key='', sep='_'):
    """
    Flatten the nested dictionary structure into a single-level dictionary.
    """
    items = []
    for k, v in data.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_data(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            for i, sub_v in enumerate(v):
                items.extend(flatten_data(sub_v, f"{new_key}{sep}{i}", sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


@app.route("/view_data/<table_name>")
def view_data(table_name):
    try:
        from Database.repository import get_table_data

        # Verwijder speciale tekens of escape de naam als nodig
        sanitized_table_name = f'"{table_name}"'

        # Controleer of de tabelnaam veilig is en correct
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        clean_table_name = table_name.strip('"')

        if clean_table_name not in tables:
            return f"Tabel '{clean_table_name}' bestaat niet in de database.", 404

        rows = get_table_data(engine, sanitized_table_name)
        if not rows:
            return f"Geen gegevens gevonden in de tabel '{table_name}'.", 404

        metadata = MetaData()
        table = Table(clean_table_name, metadata, autoload_with=engine)
        columns = table.columns.keys()

        return render_template('view_data.html', table_name=table_name, rows=rows, columns=columns)

    except Exception as e:
        tb_str = traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__)
        print("".join(tb_str))
        return f"Fout bij het ophalen van de tabel '{table_name}'.", 500


@app.route("/view_statistics")
def view_statistics():
    table_name = request.args.get('table_name', '')  # Get the table name from the query parameters
    query = request.args.get('query', '')

    print(f"Table Name: {table_name}")  # Debug output
    print(f"Query: {query}")  # Debug output

    if not table_name:
        return "Geen tabelnaam opgegeven.", 400
    if not query:
        return "Geen zoekterm opgegeven.", 400

    try:
        from Database.repository import get_statistics_data

        # Verkrijg de statistieken voor de opgegeven zoekterm in de Comp kolom
        statistics = get_statistics_data(table_name, engine, 'Comp', query)
        print(f"Statistics: {statistics}")  # Debug output
        if not statistics:
            return f"Geen statistieken gevonden voor zoekterm '{query}' in tabel '{table_name}'.", 404

        return render_template('view_statistics.html', table_name=table_name, statistics=statistics)

    except Exception as e:
        tb_str = traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__)
        print("".join(tb_str))
        return f"Fout bij het ophalen van statistieken voor '{query}' in tabel '{table_name}'.", 500


@app.route("/search")
def search():
    query = request.args.get('query', '')

    if not query:
        return "Geen zoekterm opgegeven.", 400

    try:
        from Database.repository import search_across_tables

        # Verkrijg de resultaten voor de opgegeven zoekterm
        results = search_across_tables(engine, 'Comp', query)
        if not results:
            return f"Geen resultaten gevonden voor zoekterm '{query}'.", 404

        return render_template('search_results.html', query=query, results=results)

    except Exception as e:
        tb_str = traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__)
        print("".join(tb_str))
        return f"Fout bij het ophalen van resultaten voor '{query}'.", 500


# @app.route("/b", methods=["POST", "GET"])
# def b
# @app.route("/c", methods=["POST", "GET"])
# def c
# @app.route("/d", methods=["POST", "GET"])
# def d
# @app.route("/e", methods=["POST", "GET"])
# def e
# @app.route("/f", methods=["POST", "GET"])
# def f

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
