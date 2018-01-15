import datetime
import os
import pprint
import requests

URL = 'https://hycamp.org/wsn/api/query/'
#URL = 'http://localhost:8000/wsn/api/query/'

def query(limit=100, offset=0, xbee=None, mote=None, sensor=None,
          tst__gte=None, tst__lte=None, received__gte=None, received__lte=None,
          debug=False):

    # Paramters
    if tst__gte:
        tst__gte = tst__gte.strftime('%Y-%m-%dT%H:%M:%S+00:00')
    if tst__lte:
        tst__lte = tst__gte.strftime('%Y-%m-%dT%H:%M:%S+00:00')

    params = {
        'limit': limit,
        'offset': offset,
        'mote': mote,
        'xbee': xbee,
        'sensor': sensor,
        'tst__gte': tst__gte,
        'tst__lte': tst__lte,
    }

    # Query
    headers = {'Authorization': 'Token %s' % TOKEN}
    response = requests.get(URL, headers=headers, params=params)
    response.raise_for_status()
    json = response.json()

    # Debug
    if debug:
        pprint.pprint(params)
        pprint.pprint(json)
        print()

    return json
    

if __name__ == '__main__':
    TOKEN = os.getenv('WSN_TOKEN', 'dcff0c629050b5492362ec28173fa3e051648cb1')
    response = query(
        limit=5,
        mote=161398434909148276,
        tst__gte=datetime.datetime(2017, 12, 1),
        debug=True,
    )

    response = query(
        limit=5,
        xbee=5526146534160749,
        sensor='rssi',
        received__gte=datetime.datetime(2017, 12, 1),
        debug=True,
    )
