import json
import os
import sys, time

FIELDS_TO_PARSE = ['holding_stock', 'holding_quantity']

def parse_create(payload_after):

    """Go through payload, extract needed info and save to out_tuples"""

    current_ts = time.time()

    out_tuples = []

    for field in FIELDS_TO_PARSE:

        data = (
            payload_after.get('holding_id'),
            payload_after.get('user_id'),
            field,
            None,
            payload_after.get(field),
            payload_after.get('datetime_created'),
            None,
            None, 
            current_ts            
        )

        out_tuples.append(data)

    return out_tuples


def parse_delete(payload_before, ts_ms):
    
    current_ts = time.time()

    out_tuples = []

    for field in FIELDS_TO_PARSE:

        data = (
            payload_before.get('holding_id'),
            payload_before.get('user_id'),
            field,
            payload_before.get(field),
            None,
            None, 
            ts_ms,
            current_ts            
        )

        out_tuples.append(data)

    return out_tuples

def parse_update(payload):
    
    current_ts = time.time()

    out_tuples = []

    for field in FIELDS_TO_PARSE:

        data = (
            payload.get('after', {}).get('holding_id'),
            payload.get('after', {}).get('user_id'),
            field,
            payload.get('before', {}).get('field'),
            payload.get('after', {}).get('field'),
            None,
            payload.get('ts_ms'), 
            None,
            current_ts            
        )

        out_tuples.append(data)

    return out_tuples


def parse_payload(input_raw_json):

    input_json = json.loads(input_raw_json)

    operation_type = input_json.get('payload', {}).get('op')

    if operation_type == 'c': # if it is create
        return parse_create(input_json.get('payload', {}).get('after', {}))
    
    elif operation_type == 'd':
        return parse_delete(
            input_json.get('payload', {}).get('before', {}),
            input_json.get('payload', {}).get('ts_ms', None))
    
    elif operation_type == 'u':

        return parse_update(input_json.get('payload', {}))
    
    return []

for line in sys.stdin:

    # parse payload into a format we can use and print formtted data

    data = parse_payload(line)

    for log in data:

        log_str = ','.join([str(elt) for elt in log])

        print(log_str, flush = True)
