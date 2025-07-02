import ast
import base64
import io
import os
import logging
import threading
import webbrowser

import eventlet
from flask import Flask, render_template, request, jsonify, abort
from flask_socketio import SocketIO
from matplotlib import pyplot as plt
from sqlalchemy import inspect, MetaData, Table

from sqlalchemy.orm import joinedload
from Database.repository import (
    init_db, make_table, drop_table, delete_old_file,
    get_tables, get_table_data, get_table_names,
    search_across_tables, specific_search_data,
    specific_search_data_in_all_tables, get_statistics_data, engine, Session,
)
from Database.structure import SevillaTable, Round, Game, Absence, Player
from DataReader.DataRead_file import parse_xml, emit_progress_update

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['DATABASE_PATH'] = os.path.join(os.getcwd(), 'saensepaard.db')
app.config['TEMPLATES_AUTO_RELOAD'] = True
socketio = SocketIO(app, async_mode='eventlet')

# Ensure upload folder exists
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'Data')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize DB if not present
if not os.path.isfile(app.config['DATABASE_PATH']):
    init_db()
    logger.info("Database initialized.")


### Routes ###
@app.route('/')
def home():
    return render_template('home.html')


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        files = request.files.getlist('sevFile')
        if not files or files[0].filename == '':
            return 'Geen geselecteerd bestand.', 400

        emit_progress_update(socketio, 'Start verwerking...', 0)
        total = len(files)
        feedback = None

        for idx, f in enumerate(files, start=1):
            path = os.path.join(app.config['UPLOAD_FOLDER'], f.filename)
            f.save(path)
            title, upload_date, created_date_xml, data = parse_xml(path)
            delete_old_file(path)

            feedback, status = make_table(
                sev_file=f,
                sev_index=idx,
                total_amount_sevs=total,
                upload_date=upload_date,
                created_date_xml=created_date_xml,
                data=data
            )
            if status != 200:
                return feedback, status

            emit_progress_update(socketio, f'Verzend {idx}/{total}', int(idx/total*100))

        sevs = get_tables()[::-1]
        emit_progress_update(socketio, 'Klaar!', 100)
        return render_template('upload.html', feedback=feedback, sevs=sevs)

    sevs = get_tables()[::-1]
    return render_template('upload.html', sevs=sevs)


@app.route('/upload/delete', methods=['POST'])
def delete_upload():
    sev_id = request.form.get('delete_sev_id')
    if not sev_id:
        return 'Geen ID opgegeven.', 400

    try:
        # Fetch entry
        entry = next((s for s in get_tables() if str(s.id) == sev_id), None)
        if not entry:
            return 'Niet gevonden.', 404

        # Drop and delete
        drop_table(entry.title)
        from Database.repository import Session
        session = Session()
        session.delete(entry)
        session.commit()
        session.close()

        feedback = 'Verwijderd.'
    except Exception as e:
        logger.error(f'Fout bij verwijderen: {e}')
        feedback = 'Fout opgetreden.'

    sevs = get_tables()[::-1]
    return render_template('upload.html', feedback=feedback, sevs=sevs)


@app.route('/view_data/<int:sevilla_id>')
def view_data(sevilla_id):
    session = Session()
    try:
        # Haal toernooi met gerelateerde data op (rondes, games, afwezigen, spelers)
        tournament = session.query(SevillaTable).options(
            joinedload(SevillaTable.rounds)
            .joinedload(Round.games),
            joinedload(SevillaTable.rounds)
            .joinedload(Round.absences),
            joinedload(SevillaTable.players)
        ).filter(SevillaTable.id == sevilla_id).first()

        if not tournament:
            return abort(404, f"Toernooi met id {sevilla_id} niet gevonden.")

        # Ophalen van filters (ze worden ingevuld als de button wordt ingedrukt)
        player_name_filter = request.args.get('player_name', '').strip().lower()
        plot_option = request.args.get('plot_option', 'results')
        action = request.args.get('submit_action')
        filtered_players_only_within_tournament = bool(request.args.get('player_only'))
        players_results_stacked = bool(request.args.get('players_results_stacked'))

        title = tournament.title
        jeugd_offset = 10000 if not "jeugd" in title.lower() else 0

        # Maak ID -> naam mapping
        players_dict = {p.id: p.full_name for p in tournament.players}
        print("Players dict view_data() in main.py:", players_dict)

        rounds_data = []
        print("\n")
        for rnd in sorted(tournament.rounds, key=lambda r: r.round_number or 0):
            games = []
            for g in rnd.games:
                # Zorg dat je hier de id's cast naar int als nodig
                white_id = int(g.white_player) if g.white_player is not None else None
                black_id = int(g.black_player) if g.black_player is not None else None

                games.append({
                    'white_player_id': white_id,
                    'white_player_name': players_dict.get(white_id+jeugd_offset, 'Onbekend'),
                    'black_player_id': black_id,
                    'black_player_name': players_dict.get(black_id+jeugd_offset, 'Onbekend'),
                    'result': g.result
                })

            absences = [{'player_name': a.player_name} for a in sorted(rnd.absences, key=lambda a: a.id)]

            rounds_data.append({
                'round': rnd,
                'games': games,
                'absences': absences
            })
            print(f"Ronde-datum volgens main.py: {rnd.date}")

        print(f"\ngames:\n{games}\n")

        if action == 'filter_and_plot':
            print("Filter & Plot ingedrukt.")
            print("Gekozen spelerfilter:", player_name_filter)
            print("Gekozen plotoptie:", plot_option)

        # Ophalen van resultaten per ronde voor ingevulde spelers op filterinvoer
        player_results = {}
        if action == 'filter_and_plot' and player_name_filter:
            # Matchen met behulp van substring
            matching = {pid: name for pid, name in players_dict.items()
                        if player_name_filter in name.lower()}
            for pid, pname in matching.items():
                results = []
                for rd in rounds_data:
                    outcome = None
                    for game in rd['games']:
                        if game['white_player_id'] is not None and game['white_player_id'] + jeugd_offset == pid:
                            # Gematchede speler speelde wit
                            if game['result'] == '1': outcome = 1
                            elif game['result'] == '3': outcome = 0.5
                            else: outcome = 0
                            break
                        if game['black_player_id'] is not None and game['black_player_id'] + jeugd_offset == pid:
                            # Gematchede speler speelde zwart
                            if game['result'] == '2': outcome = 1
                            elif game['result'] == '3': outcome = 0.5
                            else: outcome = 0
                            break
                    results.append(outcome)

                # Alleen spelers tellen die écht meespeelden in deze ronden
                if filtered_players_only_within_tournament:
                    # Als True, dan:
                    if any(r is not None for r in results):
                        player_results[pname] = results
                else: # Anders alle gematchede spelers weergeven ongeacht of diegene meegespeeld heeft
                    player_results[pname] = results
                print(f"Resultaat = '{results}', voor speler {pname} (ID {pid})")

            print(f"\nplayer_results van invoer spelersnaam='{player_name_filter}': {player_results}\n")

        # Alle data ophalen per persoon per ronde als geen naam is ingevuld
        elif action == 'filter_and_plot' and not player_name_filter:
            # Verzamel alle speler-IDs
            player_ids = set()
            for rd in rounds_data:
                for g in rd['games']:
                    player_ids.add(g['white_player_id'])
                    player_ids.add(g['black_player_id'])

            # Maak lege lijst per speler
            player_results = {}
            for pid in player_ids:
                pname = players_dict.get(pid + jeugd_offset, f"Speler {pid}")
                player_results[pname] = []

            # Vul per ronde de uitslag voor elke speler
            for rd in rounds_data:
                round_results = {pid: None for pid in player_ids}
                for g in rd['games']:
                    w = g['white_player_id']
                    b = g['black_player_id']
                    res = g['result']
                    if res == '1':
                        round_results[w] = 1
                        round_results[b] = 0
                    elif res == '2':
                        round_results[w] = 0
                        round_results[b] = 1
                    elif res == '3':
                        round_results[w] = 0.5
                        round_results[b] = 0.5
                    else:
                        round_results[w] = None
                        round_results[b] = None

                for pid in player_ids:
                    pname = players_dict.get(pid + jeugd_offset, f"Speler {pid}")
                    player_results[pname].append(round_results[pid])

        print(f"\nrounds_data:\n{rounds_data}\n")

        # Tot slot variabelen naar front-end sturen voor feedback
        return render_template(
            'view_data.html',
            tournament=tournament,
            rounds_data=rounds_data,
            jeugd_offset=jeugd_offset,
            players_dict=players_dict,
            plot_option=plot_option,
            player_results=player_results,
            players_results_stacked=players_results_stacked
        )
    finally:
        session.close()


@app.route('/view_statistics')
def view_statistics():
    table = request.args.get('table_name')
    query = request.args.get('query')
    if not table or not query:
        return 'Parameters missen.', 400

    stats = get_statistics_data(engine, table, 'Comp', query)
    if not stats:
        return 'Geen statistieken.', 404
    return render_template('view_statistics.html', table_name=table, statistics=stats)


@app.route('/search')
def search():
    q = request.args.get('query')
    if not q:
        return 'Geen zoekterm.', 400

    results = search_across_tables('Comp', q)
    if not results:
        return 'Geen resultaten.', 404
    return render_template('search_results.html', query=q, results=results)


@app.route('/specific_search', methods=['GET', 'POST'])
def specific_search():
    tables = get_table_names()
    if request.method == 'POST':
        term = request.form['search_term']
        tbl = request.form.get('table_name')
        if tbl:
            data = get_table_data(tbl)
            result = specific_search_data(data, term)
            columns = result.keys() if isinstance(result, dict) else []
        else:
            result = specific_search_data_in_all_tables(term)
            columns = []
        return render_template('specific_search.html', search_term=term, table_name=tbl, result=result, tables=tables, columns=columns)
    return render_template('specific_search.html', tables=tables)


@app.route('/search_suggestions')
def search_suggestions():
    tbl = request.args.get('table_name')
    term = request.args.get('search_term')
    from Database.repository import get_search_suggestions
    return jsonify(get_search_suggestions(engine, tbl, term))


if __name__ == '__main__':
    port = 5000
    url = f'http://localhost:{port}'

    # Open na 1 seconde, zodat de server opgestart is
    threading.Timer(1.0, lambda: webbrowser.open_new_tab(url)).start()


    """
    socketio.run(
        app,
        host='0.0.0.0',
        port=port,
        debug=True,
        allow_unsafe_werkzeug=True
    )
    """
    socketio.run(
        app,
        host='0.0.0.0',
        port=port,
        allow_unsafe_werkzeug=False
    )


