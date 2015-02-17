import requests
from bs4 import BeautifulSoup
import sys
import re

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
    print response.encoding
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

if __name__ == "__main__":
    kwargs = {
        'Inspection_Start': '2/1/2013',
        'Inspection_End': '2/1/2015',
        'Zip_Code': '98109'
    }
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        html, encoding = load_inspection_page()
    else:
        html, encoding = get_inspection_page(**kwargs)
    doc = parse_source(html, encoding)
    listings = extract_data_listings(doc)
    for listing in listings[:5]:
       metadata = extract_restaurant_metadata(listing)