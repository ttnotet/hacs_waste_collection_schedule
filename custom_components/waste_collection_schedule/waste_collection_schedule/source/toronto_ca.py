import requests
import csv
import json

from ..collection import Collection

from datetime import datetime, timedelta

TITLE = 'Toronto'
DESCRIPTION = (
    'Source for Toronto waste collection'
)
URL = 'https://www.toronto.ca'
CSV_URL = 'https://www.toronto.ca/ext/swms/collection_calendar.csv'
TEST_CASES = {
    "224 Wallace Ave": {"street_address": "224 Wallace Ave"},
}

PROPERTY_LOOKUP_URL = 'https://map.toronto.ca/cotgeocoder/rest/geocoder/suggest'
SCHEDULE_LOOKUP_URL = 'https://map.toronto.ca/cotgeocoder/rest/geocoder/findAddressCandidates'

ICON_MAP = {
    'GreenBin': 'mdi:compost',
    'Garbage': 'mdi:trash-can',
    'Recycling': 'mdi:recycle',
    'YardWaste': 'mdi:grass',
    'ChristmasTree': 'mdi:pine-tree',
}

PICTURE_MAP = {
    'GreenBin': 'https://www.toronto.ca/resources/swm_collection_calendar/img/greenbin.png',
    'Garbage': 'https://www.toronto.ca/resources/swm_collection_calendar/img/garbagebin.png',
    'Recycling': 'https://www.toronto.ca/resources/swm_collection_calendar/img/bluebin.png',
    'YardWaste': 'https://www.toronto.ca/resources/swm_collection_calendar/img/yardwaste.png',
}

class Source:
    def __init__(self, street_address):
        self._street_address = street_address
        
    def get_first_result(self, json_data):
        results = json_data['result']
        if len(results) == 0:
            return ''
        
        rows = results['rows']
        if len(rows) == 0:
            return ''
        
        return rows[0]
            
    def fetch(self):
        session = requests.Session()

        # lookup the address key for a particular property address
        property_download = session.get(PROPERTY_LOOKUP_URL, 
                                        params=dict(f='json', matchAddress=1, matchPlaceName=1,matchPostalCode=1,addressOnly=0,retRowLimit=100,searchString=self._street_address))
        
        property_content = property_download.content.decode('utf-8');
        property_json = json.loads(property_content);
        
        first_property_result = self.get_first_result(property_json)
        property_address_key = first_property_result['KEYSTRING']
        
        # lookup the schedule key for the above property key
        schedule_download = session.get(SCHEDULE_LOOKUP_URL, 
                                        params=dict(keyString=property_address_key, unit='%', areaTypeCode1='RESW'))
        schedule_content = schedule_download.content.decode('utf-8')
        schedule_json = json.loads(schedule_content)
        
        schedule_key = self.get_first_result(schedule_json)['AREACURSOR1']['array'][0]['AREA_NAME'].replace(' ', '')
        
        # download schedule csv and figure out what column format
        csv_download = session.get(CSV_URL)
        csv_content = csv_download.content.decode('utf-8')

        csv_lines = list(csv.reader(csv_content.splitlines(), delimiter=','))
        
        dbkey_row = csv_lines[0]
        
        id_index = dbkey_row.index('_id');
        schedule_index = dbkey_row.index('Calendar');
        week_index = dbkey_row.index('WeekStarting')
        
        format = '%Y-%m-%d'
        days_of_week = 'MTWRFSX'
        
        entries = []
        
        for row in csv_lines[1:]:
            if row[schedule_index] == schedule_key:
                pickup_date = datetime.strptime(row[week_index], format)
                startweek_day_key = pickup_date.weekday()
                
                for i in range(len(row)):
                    # skip non-waste types
                    if (i == id_index) or (i == schedule_index) or (i == week_index):
                        continue
                    
                    if row[i] not in days_of_week:
                        continue
                    
                    day_key = days_of_week.index(row[i])
                    waste_day = pickup_date + timedelta(day_key - startweek_day_key)
                    waste_type = dbkey_row[i]
                    
                    pic = PICTURE_MAP[waste_type] if waste_type in PICTURE_MAP else ""
                    icon = ICON_MAP[waste_type] if waste_type in ICON_MAP else ""
                    
                    entries.append(Collection(waste_day.date(), waste_type, picture=pic, icon=icon))
        
        return entries     
