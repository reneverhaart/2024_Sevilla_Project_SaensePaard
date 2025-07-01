import os

# Load corepackage extractor for xml
import xml.etree.ElementTree as ET

# Use dates
from datetime import datetime


def emit_progress_update(socketio, status, percentage):
    socketio.emit('update_progress', {'status': status, 'percentage': percentage})


def parse_date_safe(date_str, date_format="%d-%m-%Y %H:%M:%S"):
    date_str = date_str.strip()
    for fmt in ("%d-%m-%Y %H:%M:%S", "%d-%m-%Y", "%d-%m-%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt)
        except (ValueError, TypeError):
            pass
    return None


def parse_xml(filepath):
    tree = ET.parse(filepath)
    root = tree.getroot()

    created_date_xml = None
    title = None
    upload_date = datetime.now()
    data = {}

    for child in root:
        if child.tag == 'CONTENTS':
            for subchild in child:
                if subchild.tag == 'CREATED':
                    created_date_xml = parse_date_safe(subchild.text.strip())
        elif child.tag == 'COMP':
            data['COMP'] = parse_comp(child)
            # zoek ook naar FILENAME binnen COMP
            for comp_child in child:
                if comp_child.tag == 'FILENAME':
                    title = comp_child.text.strip()
    print(f"\nparse_xml data:\n{data}\n")

    print(f"\nparse_xml geupload bestandsnaam: {title}\n")
    return title, upload_date, created_date_xml, data


def parse_comp(comp_element):
    comp_data = {}

    # Parse rounds (bestaand)
    rounds = [parse_round(r) for r in comp_element.findall('.//ROUND')]
    comp_data['rounds'] = rounds

    # Parse players in groepen (aangepast)
    players = []
    # Zoek alle PLAYER elementen binnen GROUP elementen binnen COMP
    for group_elem in comp_element.findall('GROUP'):
        for p in group_elem.findall('PLAYER'):
            player_id = p.findtext('ID')
            playerid_ext = p.findtext('PLAYERID')  # optioneel, extern ID
            first_name = p.findtext('FIRST')
            last_name = p.findtext('LAST')
            player_data = {
                'ID': player_id,
                'PLAYERID': playerid_ext,
                'FIRST': first_name,
                'LAST': last_name
            }
            players.append(player_data)

    comp_data['players'] = players
    print(f"\nDoor parse_comp() van DataRead_file.py gedetecteerde spelers:\n{players}\n")

    # Parse overige tags behalve ROUND, GROUP
    for child in comp_element:
        if child.tag not in ['ROUND', 'GROUP']:
            comp_data[child.tag] = child.text.strip() if child.text else None

    print(f"\nDoor parse_comp() van DataRead_file.py comp_data:\n{players}\n")
    return comp_data


def parse_round(round_element):
    round_data = {}

    # Haal standaardvelden zoals ID, NAME, DATE op
    for child in round_element:
        if child.tag not in ['GAME', 'ABSENCE']:
            round_data[child.tag] = child.text.strip() if child.text else None

    print(f"\nround_data:\n{round_data}\n")

    # Voeg games toe (alleen directe kinderen, niet met './/')
    games = []
    for g in round_element.findall('GAME'):
        game_data = {
            'WHITE': g.findtext('WHITE'),
            'BLACK': g.findtext('BLACK'),
            'RES': g.findtext('RES')
        }
        games.append(game_data)
    round_data['games'] = games

    # Voeg absences toe (alleen directe kinderen)
    absences = []
    for a in round_element.findall('ABSENCE'):
        absences.append({'PLAYER': a.text.strip() if a.text else None})
    round_data['absences'] = absences

    return round_data


def parse_game(game_element):
    game = {}
    for child in game_element:
        game[child.tag] = child.text.strip() if child.text else None
    return game


def parse_abs(abs_element):
    absence = {}
    for child in abs_element:
        absence[child.tag] = child.text.strip() if child.text else None
    return absence