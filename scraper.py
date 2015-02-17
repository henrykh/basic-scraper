import requests
from bs4 import BeautifulSoup
import sys

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
        f.write(response.content)
    return response.content, response.encoding


def load_inspection_page():
    with open("inspection_page.html", 'r') as f:
        return f.read()


def parse_source(html, encoding="utf-8"):
    return BeautifulSoup(html, from_encoding=encoding)

if __name__ == "__main__":
    kwargs = {
        'Inspection_Start': '2/1/2013',
        'Inspection_End': '2/1/2015',
        'Zip_Code': '98109'
    }
    if sys.argv[1] and sys.argv[1] == 'test':
        html, encoding = load_inspection_page()
    else:
        html, encoding = get_inspection_page(**kwargs)
    doc = parse_source(html, encoding)
    print doc.prettify(encoding=encoding)
