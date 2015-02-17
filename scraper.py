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
    for listing in listings:
        metadata = extract_restaurant_metadata(listing)
        score_data = extract_score_data(listing)
        metadata["Score Data"] = score_data

        print "{}: {}\n".format("Business Name", " ".join(metadata["Business Name"]))
        print "{}: {}\n".format("Address", " ".join(metadata["Address"]))
        print "{}: {}\n".format("Longitude", " ".join(metadata["Longitude"]))
        print "{}: {}\n".format("Latitude", " ".join(metadata["Latitude"]))
        print "{}: {}\n".format("Phone", " ".join(metadata["Phone"]))
        print "{}: {}\n".format("Business Category", " ".join(metadata["Business Category"]))
        scores = ["{}: {}".format(key, value) for key, value in metadata["Score Data"].items()]
        print "{}: {}\n".format("Score Data", ", ".join(scores))

        print "\n"
