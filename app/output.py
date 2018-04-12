from flask import make_response
import csv
from io import StringIO


def oligo_to_list(oligo):
    return [oligo.get('oligo_tube'), oligo.get('oligo_name', ''),
            oligo.get('sequence', ''), oligo.get('creator_str', ''),
            oligo.get('date_added', ''), oligo.get('restrixn_site', ''),
            oligo.get('notes', '')]


def plasmid_to_list(plasmid):
    return [plasmid.get('pVD_number'), plasmid.get('plasmid_name', ''),
            plasmid.get('creator_str', ''), plasmid.get('date_added', ''),
            plasmid.get('simple_description', ''),
            plasmid.get('vector_digest', ''), plasmid.get('insert_digest', ''),
            plasmid.get('backbone', ''), plasmid.get('insert_source', ''),
            plasmid.get('copy_no_bacteria', ''),
            plasmid.get('plasmid_type', ''), plasmid.get('bac_selection', ''),
            plasmid.get('yeast_mamm_selection', ''),
            plasmid.get('promoter', ''), plasmid.get('fusion', ''),
            plasmid.get('sequenced', 0), plasmid.get('notes', '')]


def csv_response(data, dtype):
    lines = StringIO()
    writer = csv.writer(lines)
    if dtype == 'oligos':
        output = [['Oligo Tube', 'Oligo Name', 'Sequence', 'Creator',
                   'Date Added', 'Restriction Site', 'Notes']]
        for row in data:
            output.append(oligo_to_list(row))
    elif dtype == 'plasmids':
        output = [['pVD Number', 'Plasmid Name', 'Creator/Source',
                   'Date Added', 'Simple Description', 'Vector Digest',
                   'Insert Digest', 'Backbone', 'Insert Source',
                   'Bacterial Copy Number', 'Plasmid Type',
                   'Bacterial Selection', 'Yeast/Mammalian Selection',
                   'Promoter', 'Fusion', 'Sequenced', 'Notes']]
        for row in data:
            output.append(plasmid_to_list(row))
    writer.writerows(output)
    response = make_response(lines.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=records.csv'
    response.headers['Content-type'] = "text/csv"
    return response
