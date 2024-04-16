#!/usr/bin/env python3

import os
import json
import argparse

'''creates a blank jsonfile with the proper structure at the given file location'''

template = {
"contact_times":[
    {"name": "c1", "time": None, "text": "First Contact"},
    {"name": "c2", "time": None, "text": "Beginning of Totality"},
    {"name": "max","time": None, "text": "Maximum Eclipse"},
    {"name": "c3", "time": None, "text": "End of Totality"},
    {"name": "c4", "time": None, "text": "End of Eclipse"}
],
"equipment":[],
"voice_actions":[],
"camera_actions":[],
"phases":[
    {"end": "c1", "text": "Pre-Eclipse"},
    {"start": "c1", "end": "c2", "text": "Partial"},
    {"start": "c2", "end": "c3", "text": "Totality"},
    {"start": "c3", "end": "c4", "text": "Partial"},
    {"start": "c4", "text": "Post-Eclipse"}
]
}

def argparser():
    '''
    Construct a parser to parse arguments, returns the parser
    '''
    parse = argparse.ArgumentParser(description="Create a jsonfile template for an eclipse sequence.")
    parse.add_argument('--path', type=str, default='new_info.json', help="Path to save the jsonfile.")
    return parse

if __name__ == '__main__':
    args = argparser().parse_args() # parse input arguments
    with open(args.path, 'w') as file:
        json.dump(template, file, indent=2)