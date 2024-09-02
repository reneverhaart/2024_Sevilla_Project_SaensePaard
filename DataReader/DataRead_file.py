import os

# Load corepackage extractor for xml
import xml.etree.ElementTree as ET

# Use dates
from datetime import datetime


def emit_progress_update(socketio, status, percentage):
    socketio.emit('update_progress', {'status': status, 'percentage': percentage})


def parse_date(date_str, date_format="%d-%m-%Y %H:%M:%S"):
    # String to datetime parsing with format
    try:
        return datetime.strptime(date_str, date_format)
    except ValueError:
        print(f"Kan datum niet parsen: {date_str}")
        return None


def parse_xml(filepath):
    # Parse the XML file
    tree = ET.parse(filepath)
    root = tree.getroot()

    # Initialize variables to store extracted data
    created_date = None
    title = None
    data = {}

    # Loop through the XML structure and extract relevant data
    for child in root:
        for sub_child in child:
            if sub_child.tag == 'Created':
                try:
                    created_date = datetime.strptime(sub_child.text.strip(), '%d-%m-%Y %H:%M:%S')
                except ValueError:
                    print(f"Error parsing date: {sub_child.text.strip()}")

            elif sub_child.tag == 'FileName':
                title = sub_child.text.strip()

            if sub_child.tag in data:
                if isinstance(data[sub_child.tag], list):
                    data[sub_child.tag].append(sub_child.text.strip() if sub_child.text else None)
                else:
                    data[sub_child.tag] = [data[sub_child.tag], sub_child.text.strip() if sub_child.text else None]
            else:
                data[sub_child.tag] = sub_child.text.strip() if sub_child.text else None

    print(f"title={title}, date={created_date}")
    print(f"\nBegin van Data parse_xml() van DataRead_file.py:\n{data}\nEinde van Data parse_xml() van "
          f"DataRead_file.py.\n")
    return title, created_date, data


