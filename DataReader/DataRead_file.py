# Load corepackage extractor for xml
import xml.etree.ElementTree as ET


def xml_to_sql(filepath):
    # Database repository related import in function because of circular import issue
    from Database.repository import make_table

    # Load and parse the XML file
    tree = ET.parse(filepath)

    # Concept from https://stackoverflow.com/questions/58881041/store-xml-file-into-ms-sql-db-using-python
    root = tree.getroot()

    # Print out the tag of the root and all child tags
    print(root.tag)
    for child in root:
        print(child.tag, child.attrib)

    # Get all elements from XML
    columns = set()
    for elem in root.iter():
        columns.update([child.tag for child in elem])

    # Get <Created> and <FileName> values
    created_elem = root.find('Created')
    filename_elem = root.find('FileName')

    # For future: possible to check here if table already in database:
    if created_elem and filename_elem:

        # Make SQLite-table from XML columns
        table_title = make_table(columns, filename_elem, created_elem)
        print(f"Database tabel '{table_title}' is aangemaakt.")
