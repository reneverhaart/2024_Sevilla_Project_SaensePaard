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
    tree = ET.parse(filepath)
    root = tree.getroot()

    # Extracting data from the <Contents> section
    contents = root.find('Contents')
    if contents is not None:
        created_str = contents.find('Created').text
        created_date = parse_date(created_str, "%d-%m-%Y %H:%M:%S")
    else:
        created_date = None

    # Extracting data from the <Comp> section
    comps = root.findall('Comp')
    data = []
    for comp in comps:
        item = {elem.tag: elem.text for elem in comp}
        data.append(item)

    # Sorting data by the 'Name' field
    data_sorted = sorted(data, key=lambda x: x.get('Name', ''))

    return created_date, data_sorted


def xml_to_sql(filepath, socketio, session):
    # Import the necessary function inside the function to avoid circular import issues
    from Database.repository import insert_data

    # Parse the XML file to extract created_date and data
    created_date, data = parse_xml(filepath)

    if not data:
        print("Geen gegevens gevonden in het XML-bestand.")
        return

    # Define the table name and columns based on the extracted data
    sev_file = type('SevFile', (object,), {
        'filename': os.path.basename(filepath)
    })()  # Simplified structure to pass the filename

    result = make_table(sev_file, socketio, session, sev_index=1, total_amount_sevs=1, xml_columns=data[0].keys(), created_date=created_date)
    print(result)

    # Insert data into the newly created table
    if "succesvol aangemaakt" in result:
        insert_data(sev_file.filename, data)

