import os
import subprocess
import sys
import traceback


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
from Database.repository import init_db, session, make_table, get_tables, drop_old_duplicate_table, metadata, engine, \
    query_database
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
                created_date, data = parse_xml(sev_file_path)

                if not data:
                    return "Geen gegevens gevonden in het XML-bestand.", 400

                # Maak de tabel aan met de benodigde argumenten
                feedback = make_table(
                    sev_file=sev_file,
                    socketio=socketio,
                    session=session,
                    sev_index=sev_index + 1,  # Geef de huidige index door
                    total_amount_sevs=total_amount_sevs,
                    xml_columns=data[0].keys(),  # Geef de kolommen door
                    created_date=created_date  # Geef de aangemaakte datum door
                )

        # Verkrijg de tabelinformatie na verwerking van bestanden
        all_sevs = list(get_tables(session))[::-1]

        # Debug: Print de types van de objecten in `all_sevs`
        for sev in all_sevs:
            print(
                f"Type van sev: {type(sev)}, type van upload_date: {type(sev.upload_date) if hasattr(sev, 'upload_date') else 'geen upload_date'}")

        emit_progress_update(socketio, 'Verwerking voltooid!', 100)
        return render_template('upload.html', feedback=feedback, sevs=all_sevs)

    else:
        all_sevs = list(get_tables(session))[::-1]

        # Debug: Print de types van de objecten in `all_sevs`
        for sev in all_sevs:
            print(
                f"Type van sev: {type(sev)}, type van upload_date: {type(sev.upload_date) if hasattr(sev, 'upload_date') else 'geen upload_date'}")

        return render_template('upload.html', sevs=all_sevs)


@app.route("/upload/delete", methods=['POST'])
def delete_old_sev_file():
    sev_id = request.form.get('delete_sev_id')

    if sev_id:
        try:
            # Fetch the sev_file by ID
            sev_file_to_delete = session.query(SevillaTable).get(sev_id)

            if sev_file_to_delete:
                # Drop the associated table if needed
                table_name = f"{sev_file_to_delete.title}_{sev_file_to_delete.upload_date.strftime('%Y%m%d_%H%M')}".replace(
                    ' ', '_').replace('.', '_')
                drop_old_duplicate_table(table_name)

                # Delete the sev_file entry
                session.delete(sev_file_to_delete)
                session.commit()

                feedback = f'Sev file {sev_file_to_delete.title} succesvol verwijderd!'
            else:
                feedback = 'Sev file kan niet verwijderd worden, het is niet gevonden!'
        except Exception as e:
            session.rollback()
            print(f"Error occurred while deleting sev file: {e}")
            feedback = "Er is een fout opgetreden bij het verwijderen van het sev-bestand."
    else:
        feedback = "Geen Sev ID opgegeven."

    all_sevs = list(get_tables(session))[::-1]
    return render_template('upload.html', feedback=feedback, sevs=all_sevs)


@app.route("/view_table/<table_name>")
def view_table(table_name):
    try:
        rows, columns = query_database(table_name)

        if rows is None:
            return f"Fout bij het ophalen van de tabel '{table_name}'.", 500

        if not rows:
            return f"Geen gegevens gevonden in de tabel '{table_name}'.", 404

        # Render Data in template
        return render_template('view_table.html', table_name=table_name, rows=rows, columns=columns)
    except Exception as e:
        tb_str = traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__)
        print("".join(tb_str))  # Traceback for debugging
        return f"Fout bij het ophalen van de tabel '{table_name}'.", 500


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
