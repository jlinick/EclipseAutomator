#!/usr/bin/env python3

import os
import json
import datetime
import requests
import argparse
import pytz
from dateutil import parser
from timezonefinder import TimezoneFinder 

'''retrieves the specific eclipse timings given your lat, lon, height, and eclipse date'''

def get_eclipse_times(lat, lon, height, date):
    '''retrieves the specific eclipse timings given your lat (decimal), lon (decimal), height (meters), and eclipse date'''
    formatted_date = format_date(date)
    formatted_coords = f'{lat},{lon}'
    url = f'https://aa.usno.navy.mil/api/eclipses/solar/date?date={formatted_date}&coords={formatted_coords}&height={height}'
    response = requests.get(url) # Make the get request
    if not response.status_code == 200:
        raise Exception('query not returning valid data, check lat/lon/dates for valid inputs') # if the request was unsuccessful
    tz = get_timezone(lat, lon)
    print('timezone of given location is: {}'.format(tz))
    return parse_times(response.json(), tz)

def get_eclipses(year):
    '''get a list of eclipse datetime dates for the given year'''
    url = f'https://aa.usno.navy.mil/api/eclipses/solar/year?year={year}'
    response = requests.get(url) # Make the get request
    if not response.status_code == 200:
        raise Exception('unable to query for eclipse datetimes') # if the request was unsuccessful
    eclipses = response.json()['eclipses_in_year']
    tot_eclipses = [e for e in eclipses if 'Total' in e.get('event', '')]
    return [datetime.date(ec.get('year',0), ec.get('month',0), ec.get('day',0)) for ec in tot_eclipses]

def get_total_eclipses(year):
    '''returns a list of datetime dates for total eclipses for the given year'''
    url = f'https://aa.usno.navy.mil/api/eclipses/solar/year?year={year}'
    response = requests.get(url) # Make the get request
    if not response.status_code == 200:
        raise Exception('unable to query for eclipse datetimes') # if the request was unsuccessful
    eclipses = response.json()['eclipses_in_year']
    return [datetime.date(ec.get('year',0), ec.get('month',0), ec.get('day',0)) for ec in eclipses]

def get_next_total_eclipse():
    '''returns the date object for the next total eclipse'''
    day = datetime.date.today()
    next_eclipse = None
    year = day.year
    while next_eclipse is None:
        next_eclipse = min([e for e in get_total_eclipses(year) if e >= day], default=None)
        year = year+1
    return next_eclipse

def format_date(input_date):
    if isinstance(input_date, str): # if the input is a string
        try:
            input_date = datetime.datetime.strptime(input_date, "%Y-%m-%d")
        except ValueError:
            input_date = parser.parse(input_date) # parse into a datetime object
    if isinstance(input_date, datetime.datetime) or isinstance(input_date, datetime.date):
        return input_date.strftime("%Y-%m-%d") # Format and return the date string
    raise Exception('invalid input date')

def parse_times(input_json, timezone):
    '''parses the times from the input json and converts them into datetime objects, and returns them as a mapped dictionary'''
    prop = input_json.get('properties', {})
    e_date = datetime.date(prop.get('year',0), prop.get('month',0), prop.get('day',0))
    pmap = {'Eclipse Begins': None,'Totality Begins':None,'Maximum Eclipse': None,'Totality Ends': None,'Eclipse Ends': None}
    ld_lst = prop.get('local_data', [])
    for ev in ld_lst:
        p = ev.get('phenomenon')
        if p in pmap:
            pmap[p] = ev.get('time')
    # converts the times into properly timezone formatted list, then a key,value pair mapped dict (where the keys are c1,c2,max,c3,c4 as in the json schema)
    time_values = [combine(e_date, pmap.get(t), timezone).isoformat() for t in ['Eclipse Begins','Totality Begins','Maximum Eclipse','Totality Ends','Eclipse Ends']]
    return dict(zip(['c1', 'c2', 'max', 'c3', 'c4'], time_values))

def combine(date, time_string, timezone):
    '''combines the date object and time string to generate a datetime object, sets the timezone explicitly to utc, then formats it to the given timezone'''
    return datetime.datetime.combine(date, datetime.datetime.strptime(time_string, '%H:%M:%S.%f').time()).replace(tzinfo=pytz.utc).astimezone(timezone)

#def to_str(dt, timezone):
#    '''takes the datetime object and returns it as an iso formatted stringreturns in a formatted string with timezone'''
#    if dt.tzinfo is None:    
#        return dt.astimezone(timezone)isoformat() # the datetimes returned from usno are in UTC
#    return dt.astimezone(timezone)isoformat() # Format as ISO
        
def get_timezone(lat, lon):
    '''returns the timezone object for the given lat and lon'''
    timz = TimezoneFinder() 
    return pytz.timezone(timz.timezone_at(lng=lon, lat=lat))

def update_event_times(file_path, time_mapping):
    # Load the JSON data from the file
    with open(file_path, 'r') as file:
        data = json.load(file)
    # Check if 'events' key exists in the JSON data
    if 'events' in data:
        # Iterate over each event in the list
        for event in data['events']:
            # If the event's name is in the time_mapping dictionary, update its time
            if event['name'] in time_mapping:
                event['time'] = time_mapping[event['name']]
    # Save the modified data
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=2)

def run(json_file, lat, lon, height, date=None, noupdate=False):
    '''main function that validates inputs, queries for eclipse times, and prints/saves the result'''
    if not os.path.exists(json_file):
        raise Exception(f'json file does not exist: {json_file}')
    if not -90 <= lat <= 90:
        raise Exception(f'latitude not within proper bounds: {lat}')
    if not -180 <= lon <= 180:
        raise Exception(f'longitude not within proper bounds: {lon}')
    if date is None:
        date = get_next_total_eclipse()
        print(f'querying over next eclipse on {date}')
    date = format_date(date)
    # retrieve the eclipse time mappings
    tim_map = get_eclipse_times(lat, lon, height, date)
    print('found eclipse times:',*tim_map.items())
    if noupdate:
        return
    # update the json
    print(f'updating json file: {json_file}...')
    update_event_times(json_file, tim_map)
    print('update complete.')

def argparser():
    '''
    Construct a parser to parse arguments, returns the parser
    '''
    parse = argparse.ArgumentParser(description="Run Eclipse Automator for controlling USB and Serial Cameras")
    parse.add_argument('--input', type=str, default='info.json', help="Path to the JSON config file. Default is 'info.json'.")    
    parse.add_argument('--lat', required=True, type=float, help='Decimal latitude of your location (within the path of totality)')
    parse.add_argument('--lon', required=True, type=float, help='Decimal longitude of your location (within the path of totality)')
    parse.add_argument('--height', required=False, type=int, default=0, help='Integer height of your observing location (meters)')
    parse.add_argument('--date', required=False, default=None, help='Date of the eclipse YYYY-MM-DD (defaults to the next total eclipse)')
    parse.add_argument("--noupdate", action='store_true', default=False, help="prints the datetimes, but does not update the jsonfile")
    return parse


if __name__ == '__main__':
    args = argparser().parse_args() # parse input arguments
    run(args.input, args.lat, args.lon, args.height, date=args.date, noupdate=args.noupdate)
