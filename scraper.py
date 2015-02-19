import requests
from bs4 import BeautifulSoup
from operator import itemgetter
import argparse
import json
import string
import sys
import re
import geocoder

INSPECTION_DOMAIN = 'http://info.kingcounty.gov/'
INSPECTION_PATH = '/health/ehs/foodsafety/inspections/Results.aspx'
QUERY_PARAMS = {
    'Output': 'W',
    'Business_Name': '',
    'Business_Address': '',
    'Longitude': '',
    'Latitude': '',
    'City': '',
    'Zip_Code': '',
    'Inspection_Type': 'All',
    'Inspection_Start': '',
    'Inspection_End': '',
    'Inspection_Closed_Business': 'A',
    'Violation_Points': '',
    'Violation_Red_Points': '',
    'Violation_Descr': '',
    'Fuzzy_Search': 'N',
    'Sort': 'H'
}


def get_inspection_page(**kwargs):
    url = INSPECTION_DOMAIN + INSPECTION_PATH
    params = QUERY_PARAMS.copy()
    for key, value in kwargs.items():
        if key in QUERY_PARAMS:
            params[key] = value
    response = requests.get(url, params=params)
    response.raise_for_status()
    with open("inspection_page.html", 'w') as f:
        f.write("{}\n".format(response.encoding))
        f.write(response.content)
    return response.content, response.encoding


def load_inspection_page():
    with open("inspection_page.html", 'r') as f:
        encoding = f.readline()
        content = f.read()
        return content, encoding


def parse_source(html, encoding="utf-8"):
    return BeautifulSoup(html, from_encoding=encoding)


def extract_data_listings(parsed_doc):
    container_finder = re.compile(r'PR[\d]+~')
    return parsed_doc.find_all('div', id=container_finder)


def has_two_tds(element):
    td_children = element.find_all('td', recursive=False)
    return element.name == 'tr' and len(td_children) == 2


def clean_data(td):
    data = td.string
    try:
        return data.strip(" \n:-")
    except AttributeError:
        return u""


def extract_restaurant_metadata(listing):
    metadata_rows = listing.find('tbody').find_all(
        has_two_tds, recursive=False)
    restaurant_data = {}
    current_label = ''
    for row in metadata_rows:
        key_cell, val_cell = row.find_all('td', recursive=False)
        new_label = clean_data(key_cell)
        current_label = new_label if new_label else current_label
        restaurant_data.setdefault(current_label, []).append(
            clean_data(val_cell))
    return restaurant_data


def is_inspection_row(element):
    is_tr = element.name == 'tr'
    if not is_tr:
        return False
    child_tds = element.find_all('td', recursive=False)
    this_text = clean_data(child_tds[0]).lower()
    contains_word = 'inspection' in this_text
    does_not_start = not this_text.startswith('inspection')
    return element.name == 'tr' and len(
        child_tds) == 4 and contains_word and does_not_start


def extract_score_data(listing):
    inspection_rows = listing.find_all(is_inspection_row)
    samples = len(inspection_rows)
    total = high_score = average = 0
    for row in inspection_rows:
        strval = clean_data(row.find_all('td')[2])
        try:
            intval = int(strval)
        except:
            samples -= 1
        else:
            total += intval
            high_score = intval if intval > high_score else high_score
    if samples:
        average = total/float(samples)
    data = {
        u'Average Score': average,
        u'High Score': high_score,
        u'Total Inspections': samples
    }
    return data


def generate_results(sorter=None, count=10,):
    kwargs = {
        'Inspection_Start': '2/1/2013',
        'Inspection_End': '2/1/2015',
        'Zip_Code': '98109'
    }
    if True:
        html, encoding = load_inspection_page()
    else:
        html, encoding = get_inspection_page(**kwargs)
    doc = parse_source(html, encoding)
    listings = extract_data_listings(doc)
    total_metadata = []
    for listing in listings:
        metadata = extract_restaurant_metadata(listing)
        score_data = extract_score_data(listing)
        metadata.update(score_data)
        total_metadata.append(metadata)

    if sorter:
        sorter = string.capwords(sorter.replace("_", " "))

    total_metadata = sorted(total_metadata, key=itemgetter(sorter), reverse = True)

    for listing in total_metadata[:count]:
        yield listing


def get_geojson(result):
    address = " ".join(result.get('Address', ''))
    if not address:
        return None
    geocoded = geocoder.google(address)
    geojson = geocoded.geojson
    inspection_data = {}
    use_keys = (
        'Business Name', 'Average Score', 'Total Inspections', 'High Score',
        'Address',
    )
    for key, val in result.items():
        if key not in use_keys:
            continue
        if isinstance(val, list):
            val = " ".join(val)
        inspection_data[key] = val
    new_address = geojson['properties'].get('address')
    if new_address:
        inspection_data['Address'] = new_address
    geojson['properties'] = inspection_data
    return geojson


if __name__ == "__main__":
    import pprint
    parser = argparse.ArgumentParser("Score Sorting")
    parser.add_argument('--sort', choices=("high_score", "average_score", "total_inspections"))
    args = parser.parse_args()
    # test = len(sys.argv) > 1 and sys.argv[1] == 'test'
    total_result = {'type': 'FeatureCollection', 'features': []}
    for result in generate_results(args.sort):
        geo_result = get_geojson(result)
        pprint.pprint(geo_result)
        total_result['features'].append(geo_result)
    with open('my_map.json', 'w') as fh:
        json.dump(total_result, fh)
