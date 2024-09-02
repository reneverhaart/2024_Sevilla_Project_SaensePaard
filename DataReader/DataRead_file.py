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
    def parse_element(element):
        """
        Recursively parse XML elements and their children into a dictionary.
        """
        data = {}
        for child in element:
            if len(child):
                # If the child has sub-children, recursively parse them
                if child.tag not in data:
                    data[child.tag] = []
                data[child.tag].append(parse_element(child))
            else:
                # Otherwise, store the text content of the child
                data[child.tag] = child.text.strip() if child.text else None
        return data

    # Parse the XML file
    tree = ET.parse(filepath)
    root = tree.getroot()

    # Initialize variables to store extracted data
    created_date = None
    title = None
    data = {}

    # Loop through the root and extract relevant data
    for child in root:
        if child.tag == 'Created':
            try:
                created_date = datetime.strptime(child.text.strip(), '%d-%m-%Y %H:%M:%S')
            except (ValueError, AttributeError) as e:
                print(f"Error parsing date: {child.text.strip() if child.text else 'None'} - {e}")
        elif child.tag == 'FileName':
            title = child.text.strip()
        else:
            # Use the parse_element function to handle nested elements
            data[child.tag] = parse_element(child)

    # If created_date is None, set a default value
    if created_date is None:
        created_date = datetime.now()  # or any other default value you deem appropriate

    print(f"title={title}, date={created_date}")
    print(f"\nBegin van Data parse_xml() van DataRead_file.py:\n{data}\nEinde van Data parse_xml() van "
          f"DataRead_file.py.\n")
    return title, created_date, data


