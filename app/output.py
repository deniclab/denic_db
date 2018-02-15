from flask import make_response
import csv
from io import StringIO


def oligo_to_list(oligo):
    return [oligo.get('oligo_tube'), oligo.get('oligo_name', ''),
            oligo.get('sequence', ''), oligo.get('creator_str', ''),
            oligo.get('date_added', ''), oligo.get('restrixn_site', ''),
            oligo.get('notes', '')]


def csv_response(data):
    lines = StringIO()
    writer = csv.writer(lines)
    oligos = [['Oligo Tube', 'Oligo Name', 'Sequence', 'Creator', 'Date Added',
               'Restriction Site', 'Notes']]
    for oligo in data:
        oligos.append(oligo_to_list(oligo))
    writer.writerows(oligos)
    response = make_response(lines.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=oligo_output.csv'
    response.headers['Content-type'] = "text/csv"
    return response
