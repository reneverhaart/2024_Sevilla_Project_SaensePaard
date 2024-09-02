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
        print(f"Tag: {child.tag}, Attrib: {child.attrib}")  # Optional: For debugging

        # Check if the child has any sub-elements
        for sub_child in child:
            print(f"  Sub-tag: {sub_child.tag}, Text: {sub_child.text}")

            if sub_child.tag == 'Created':
                # Parse the 'Created' value as a datetime object
                try:
                    created_date = datetime.strptime(sub_child.text.strip(), '%d-%m-%Y %H:%M:%S')
                except ValueError:
                    print(f"Error parsing date: {sub_child.text.strip()}")

            elif sub_child.tag == 'FileName':
                # Store the 'FileName' value in title
                title = sub_child.text.strip()

            # Add sub-child tag and text to the dictionary
            data[sub_child.tag] = sub_child.text.strip() if sub_child.text else None

            # Add sub-child tag and text to the dictionary
            if sub_child.tag in data:
                # If key exists, append the new value to the list
                if isinstance(data[sub_child.tag], list):
                    data[sub_child.tag].append(sub_child.text.strip() if sub_child.text else None)
                else:
                    data[sub_child.tag] = [data[sub_child.tag], sub_child.text.strip() if sub_child.text else None]
            else:
                data[sub_child.tag] = sub_child.text.strip() if sub_child.text else None

    print(f"title={title}, date={created_date}")

    return title, created_date, data


def xml_to_sql(filepath, socketio, session):
    # Import the necessary function inside the function to avoid circular import issues
    from Database.repository import insert_data, make_table

    # Parse the XML file to extract title, created_date, and sorted data
    title, created_date, data_sorted = parse_xml(filepath)

    if not data_sorted:
        print("Geen gegevens gevonden in het XML-bestand.")
        return

    # Define the table name and columns based on the extracted data
    sev_file = type('SevFile', (object,), {
        'filename': os.path.basename(filepath)
    })()  # Simplified structure to pass the filename

    # Create the table using the extracted columns and metadata
    result = make_table(xml_columns=data_sorted[0].keys(), title=title, created_date=created_date)

    print(result)

    # Insert data into the newly created table
    if "succesvol aangemaakt" in result.lower():
        insert_data(sev_file.filename, data_sorted)
    else:
        print("Tabel werd niet aangemaakt. Geen gegevens ingevoerd.")


