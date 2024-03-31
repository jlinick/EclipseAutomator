#!/usr/bin/env python3

import sys
import os
import re
import math
import serial
import time
import datetime
import json
import time
import glob
import subprocess
import queue
import threading
from dateutil import parser
import warnings
import logging
import argparse

'''Script for automating eclipse based on known c1,c2,c3,c4 datetimes'''

logging.basicConfig(filename='run.log', level=logging.DEBUG, filemode='a', format='%(asctime)s : %(name)s : %(levelname)s : %(message)s')

# shutters allowed by camera
allowable_shutters = ["1/8000","1/6400", "1/5000", "1/4000", "1/3200", "1/2500", "1/2000",
 "1/1600", "1/1250", "1/1000", "1/800", "1/640", "1/500", "1/400", "1/320",
  "1/250", "1/200", "1/160", "1/125", "1/100", "1/80", "1/60", "1/50", "1/40", "1/30",
  "1/25", "1/20", "1/15", "1/13", "1/10", "1/8", "1/6", "1/5", "1/4", "0.3", "0.4", "0.5",
  "0.6", "0.8", "1","1.3","1.6", "2", "2.5", "3.2", "4", "5", "6.3", "8", "10.3", "13", 
  "15", "20", "25", "30"]
shutters = {eval(s): s for s in allowable_shutters}

# if string is specified, shutter speed is calculated using https://umbra.nascom.nasa.gov/eclipse/980226/tables/table_26.html
allowable_targets = ['Partial, ND 4.0', 'Partial, ND 5.0', 'Baily\'s Beads', 'Chromosphere', 'Prominences', 'Corona - 0.1 Rs',
        'Corona - 0.2 Rs', 'Corona - 0.5 Rs', 'Corona - 1.0 Rs', 'Corona - 2.0 Rs', 'Corona - 4.0 Rs', 'Corona - 8.0 Rs']

class EclipseAutomation():
    '''main object for running eclipse automation loop'''
    
    def __init__(self, test=None, inputfile='input.json', nodisplay=False, nosound=False, noinput=False, verbose=False):
        logging.info('starting imports for optional libraries.') # imports for optional libraries
        self.test = test
        self.inputfile = inputfile
        self.nodisplay = nodisplay
        self.nosound = nosound
        self.noinput = noinput
        self.verbose = verbose
        logging.info('initializing objects and parsing json')
        self.t = Timeholder(inputfile) # parses json, creates event/phase/action objects
        if not test is None:
            self.t.start_test(offset=test, event='c2') # test mode
        self.dispatcher = CameraDispatch(self.t.json_obj) # instantiate the dipatch object, which will create camera objects, threads and queues
        if nodisplay is False:
            self.layout = self.init_layout()
        if nosound is False:
            self.announce() # nice little init announcement
        if noinput is False:
            self.init_keyboard_listener()
        self.run() # run the camera/announcement/update screen loop
                 
    def run(self):
        '''main loop'''
        logging.info('Starting main loop.')
        if self.nodisplay is False:
            with rich.live.Live(self.layout, refresh_per_second=10, screen=True):
                self.loop()
        else:
            self.loop()
        self.dispatcher.complete()

    def loop(self):
        '''main loop that dispatches actions and refreshes the screen'''
        while(not self.is_over()):
            now = self.t.get_now()
            # run camera actions
            cactions = self.t.camera_actions.get_allowable(now)
            for caction in cactions:
                self.dispatcher.dispatch_action(caction)
             # run voice actions
            if self.nosound is False:
                vactions = self.t.get_voice_actions()
                for va in vactions:
                    va.play()
            # update the layout
            if self.nodisplay is False:
                self.update_layout()
            time.sleep(.01)

    def is_over(self):
        '''returns True if the eclipse is over, and there are no more actions left'''
        now = self.t.get_now()
        if not self.t.events.is_post_eclipse(now):
            return False
        if not self.t.camera_actions.get_next_action(now) is None:
            return False
        if not self.t.voice_actions.get_next_action(now) is None:
            return False
        return True

    def init_layout(self):
        '''initialize the display layout'''
        if self.nodisplay is False:
            layout = rich.layout.Layout()
        # Create layout components
        header = rich.layout.Layout(name="header", size=11)
        main = rich.layout.Layout(name="main", ratio=1) # (timer) and (two tables)
        footer = rich.layout.Layout(name="footer", size=10)
        # Add components to the layout
        layout.add_split(header)
        layout.add_split(main)
        layout.add_split(footer)
        timer = rich.layout.Layout(name="timer", size=9)
        body = rich.layout.Layout(name="body", ratio=1)
        main.add_split(timer)
        main.add_split(body)
        body.split(rich.layout.Layout(name="upper"), rich.layout.Layout(name="lower"))
        return layout

    def update_layout(self):
        '''updates the panels with current information'''
        now = self.t.get_now()
        self.layout['header'].update(self.gen_title_panel())
        self.layout['timer'].update(self.gen_timer_panel())
        self.layout["body"]["upper"].update(self.gen_current_table())
        self.layout["body"]["lower"].update(self.gen_upcoming_table())
        self.layout['footer'].update(self.gen_info_table())

    def gen_title_panel(self):
        now = self.t.get_now()
        dat = now.strftime('%B %-d, %Y (%Z)')
        tim = now.strftime('%I:%M:%S %p')
        date_text = rich.text.Text(dat, style="b blue")
        bigtime = pyfiglet.Figlet(font="moscow").renderText(tim).replace("#", "█")
        time_text = rich.text.Text(bigtime, style="b green")
        date_aligned = rich.align.Align.center(date_text)
        time_aligned = rich.align.Align.center(time_text)
        combined_text = rich.console.Group(date_aligned, time_aligned) # Use a Group to combine the centered Text objects
        # Create the panel with the combined Text objects
        title_panel = rich.panel.Panel(
            combined_text,
            box=rich.box.ROUNDED,
            padding=(1, 1),
            title='Eclipse Automator',
            subtitle='by Justin Linick',
            border_style="blue",
        )
        return title_panel

    def gen_timer_panel(self):
        now = self.t.get_now()
        nexte = self.t.get_next_event()
        time_until = format_hms(now, nexte)
        #txt = '{} until {}'.format(time_until, nexte)
        next_phase = rich.align.Align.center(rich.text.Text(f'{nexte} in ', style="yellow"))
        bigtxt = pyfiglet.figlet_format(time_until, font='moscow', width=150)
        blocktxt = rich.align.Align.center(rich.text.Text(re.sub(r'[0-9#:]', "█", bigtxt), style="b green"))
        combined_text = rich.console.Group(next_phase, blocktxt)
        return combined_text

    def gen_current_table(self):
        '''generates the table for upcoming camera actions'''
        now = self.t.get_now()
        actions = self.t.camera_actions.get_current(now)
        table = rich.table.Table(title='Current Camera Actions', expand=True)
        #table.add_column("(sec)", justify="center", style="cyan", no_wrap=True, min_width=10)
        table.add_column("Time Remaining (sec)", min_width=30)
        table.add_column("Type", style="magenta", min_width=30)
        table.add_column("Camera ID", style="green", min_width=20)
        table.add_column("Shutter", style="yellow")
        table.add_column("Int", justify="right", style="green", min_width=20)
        for act in actions:
            dt =  act.time_left()
            tstr = '{:.1f}'.format(dt)
            progbar = progressbar(dt, length=30, max_sec=30)
            typ = act.text
            cam_id = self.dispatcher.get_camera_id(act)
            shutt = self.dispatcher.cameras.get(cam_id).determine_shutter(act)
            intvl = str(int(act.interval)) if act.interval is not None else ''
            if act.is_active():
                int_txt = rich.text.Text(intvl, style="on yellow")
            else:
                int_txt = rich.text.Text(intvl, style="on black")
            table.add_row(progbar, str(typ), str(cam_id), str(shutt), int_txt)
        return table

    def gen_upcoming_table(self, n=10):
        '''generates the table for upcoming camera actions'''
        now = self.t.get_now()
        actions = self.t.camera_actions.get_next_n_actions(now, n)
        table = rich.table.Table(title='Upcoming Camera Actions', expand=True)
        table.add_column("Time Until Action Initiates (sec)", justify='left', min_width=40, max_width=40)
        table.add_column("Type", style="magenta", min_width=30)
        table.add_column("Camera ID", style="green", min_width=20)
        table.add_column("Shutter", style="yellow")
        table.add_column("Duration", justify="right", style="green", min_width=20)
        table.add_column("Int", justify="right", style="green")
        for act in actions:
            dt = act.time_until()
            tstr = '{:.1f}'.format(dt)
            progbar = progressbar(dt, length=40, max_sec=40)
            typ = act.text
            cam_id = self.dispatcher.get_camera_id(act)
            shutt = self.dispatcher.cameras.get(cam_id).determine_shutter(act)
            dur = progressbar(act.duration(), length=30, max_sec=30, text_left=False)
            intvl = str(int(act.interval)) if act.interval is not None else ''
            table.add_row(progbar, str(typ), str(cam_id), str(shutt), dur, str(intvl))
        return table

    def gen_info_table(self):
        table = rich.table.Table(title='Info', box=None)
        table.add_column('Camera ID',justify="left", style="green")
        table.add_column('Current Shutter Speed', justify="center", style="yellow")
        table.add_column('Focal Ratio', justify="center", style="blue")
        table.add_column('Active', justify="center", style="blue")
        table.add_column('USB Port', justify="center", style="blue")
        table.add_column('Serial Port', justify="center", style="blue")
        table.add_column('EF', justify="center", style="red")
        for camera in self.dispatcher.cameras.values():
            cam_id = str(camera.camera_id)
            shut = str(camera.current_shutter)
            fstop = str(camera.f_ratio)
            isact = camera.currently_active
            usb = str(camera.usb_port)
            serial = str(camera.serial_port)
            ef = f'{camera.enhancement_factor:.1f}'
            if isact:
                acttxt = rich.text.Text('', style="on yellow")
            else:
                acttxt = rich.text.Text('', style="on black")
            table.add_row(cam_id, shut, fstop, acttxt, usb, serial, ef)
        return rich.align.Align.center(table)

    def announce(self):
        curr_time = self.t.get_now()
        curr_phase = self.t.get_current_phase()
        next_event = self.t.get_next_event()
        saystr = 'We are currently in the {} phase. {} until {}'.format(self.t.get_current_phase(),
            format_timedelta(curr_time, next_event.time), next_event)
        say(saystr)

    def init_keyboard_listener(self):
        listener = keyboard.Listener(on_press=self.on_press)
        listener.start()
        logging.info('Initialized keyboard listener.')

    def on_press(self, key):
        try:
            if key == keyboard.Key.up:
                self.enhancement_up()
            elif key == keyboard.Key.down:
                self.enhancement_down()
            elif key == keyboard.Key.esc:
                self.exit()
        except AttributeError as e:
            logging.error(f'Error in key press: {e}')

    def enhancement_up(self):
        logging.info(f'raising enhancement factor')
        for camera in self.dispatcher.cameras.values():
            cam_id = camera.camera_id
            ef = camera.enhancement_factor
            new_ef = ef + 0.1
            logging.info(f'raising enhancement factor of {cam_id} from {ef:.2f} to {new_ef:.2f}')
            camera.enhancement_factor = new_ef

    def enhancement_down(self):
        for camera in self.dispatcher.cameras.values():
            cam_id = camera.camera_id
            ef = camera.enhancement_factor
            new_ef = ef - 0.1
            logging.info(f'raising enhancement factor of {cam_id} from {ef:.2f} to {new_ef:.2f}')
            camera.enhancement_factor = new_ef

    def exit(self):
        logging.info('intercepted exit signal! exiting.')
        self.dispatcher.complete()
        sys.exit()

class RichOutput:
    def __init__(self, layout, name):
        self.layout = layout
        self.name = name
        self.console = rich.console.Console()

    def write(self, text):
        if text.strip():  # Avoid printing empty lines
            self.layout[self.name].update(rich.text.Text(text))

    def flush(self):
        pass  # No need


class Timeholder():
    '''parses the json, determines times, and handles event and datetime objects'''
    local_tz = None # used to hold local timezone information

    def __init__(self, jsonfile, offset=0):
        self.offset = offset # time offset used to emulate an eclipse
        self.phases = None
        self.events = None
        self.voice_actions = None

        json_obj = self.parse_json(jsonfile)
        self.build_events(json_obj)
        self.build_phases(json_obj)
        self.build_actions(json_obj)
        self.json_obj = json_obj
    
    def start_test(self, event='c2', offset=-75):
        '''sets the offset so an *eclipse* starts. c2 offset is how many seconds relative to c2 the test starts'''
        self.offset = self.events.get(event) - self.get_now() + int(offset)

    def get_voice_actions(self):
        '''returns a list of any voice action objects that are occurring right now'''
        return self.voice_actions.get(self.get_now())

    def get_camera_actions(self):
        '''returns a list of any camera action objects that should be active right now'''
        return self.camera_actions.get(self.get_now())

    def get_phase(self):
        return self.phases.get(self.get_now())

    def get_now(self):
        '''returns now. may change in the future so use this'''
        return datetime.datetime.now(datetime.timezone.utc).astimezone() + datetime.timedelta(seconds=self.offset)

    def parse_json(self, jsonfile):
        # parse the event_times json object
        if not os.path.exists(jsonfile):
            logging.error(f'{jsonfile} does not exist! Exiting.')
            raise Exception(f'{jsonfile} does not exist! Exiting.')
        with open(jsonfile, 'r') as file:
            json_obj = json.load(file)
        return json_obj

    def build_events(self, json_obj, verbose=False):
        self.events = Events(json_obj, self.get_local_tz())
        if verbose:
            print('--Events--')
            [print(a) for a in self.events.events]
            print(self.events.events)

    def build_phases(self, json_obj, verbose=False):
        self.phases = Phases(json_obj, self.events)
        if verbose:
            print('--Phases--')
            [print(a) for a in self.phases.phases]
            print(self.phases.phases)

    def build_actions(self, json_obj, verbose=False):
        self.camera_actions = CameraActions(json_obj, self.events, self.get_now)
        if verbose:
            logging.info('--Camera Actions--')
            [logging.info(a) for a in self.camera_actions.actions]
            logging.info(self.camera_actions.actions)
        self.voice_actions = VoiceActions(json_obj, self.events, self.get_now)
        if verbose:
            logging.info('--Voice Actions--')
            [logging.info(a) for a in self.voice_actions.actions]
            logging.info(self.voice_actions.actions)

    def get_local_tz(self):
        '''returns the local timezone, saves as class object (referenced outside class)'''
        if self.local_tz is None:
            self.local_tz = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
            return self.local_tz
        return self.local_tz

    def string_to_dt(self, input_string):
        '''parses a string and returns a datetime in the local timezone'''
        local_tz = self.get_local_tz()
        return datetime.datetime.strptime(input_string, "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=local_tz)

    def get_next_event(self):
        '''returns the next event'''
        return self.events.get_next_event(self.get_now())

    def get_next_voice_action(self):
        return self.voice_actions.get_next_action(self.get_now())

    def get_next_camera_action(self):
        return self.camera_actions.get_next_action(self.get_now())

    def get_next_phase(self):
        return self.phases.get_next_phase(self.get_now())

    def get_current_phase(self):
        return self.phases.get(self.get_now())


class Events():
    '''holds event objects'''
    def __init__(self, json_obj, tzinfo):
        self.tzinfo = tzinfo
        self.events = []
        events_list = json_obj.get('events', [])
        # parse the json dict and create events
        for ev in events_list:
            self.events.append(Event(ev, tzinfo))

    def get_events(self):
        return self.events

    def get_next_event(self, now):
        return min([e for e in self.events if e >= now], default=None)

    def get(self, name):
        return next((e for e in self.events if e == name), None)

    def get_time(self, name):
        return next((e.time for e in self.events if e == name), None)

    def is_post_eclipse(self, now):
        '''returns True if eclipse is over, False otherwise'''
        return now > self.get('c4')

class Event():
    '''represents specific event times for c1, c2, c3, c4'''
    def __init__(self, event_dict, tzinfo):
        self.name = event_dict.get('name', 'unknown')
        tm = event_dict.get('time', None)
        self.time = datetime.datetime.strptime(tm, "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=tzinfo)
        try:
            self.time = parser.parse(tm).replace(tzinfo=tzinfo)
        except:
            logging.error(f'unable to parse input time: {tm}')
            raise Exception(f'unable to parse input time: {tm}')
        self.text = event_dict.get('text', 'unknown')
        logging.info(f'parsed time of event {self.text}: {self.time}')

    def get_time(self):
        return self.time

    def __eq__(self, other):
        '''if other is a datetime object, does a comparison'''
        if isinstance(other, datetime.datetime):
            if self - other <= 0 and self - other > -1:
                return True
            return False
        if isinstance(other, str):
            if self.name == other:
                return True
            return False
        return NotImplemented

    def __gt__(self, other):
        '''if other is a datetime object, does a comparison'''
        if isinstance(other, datetime.datetime):
            return self.time > other
        if isinstance(other, Event):
            return self.time > other.time
        return NotImplemented

    def __lt__(self, other):
        '''if other is a datetime object, does a comparison'''
        if isinstance(other, datetime.datetime):
            return self.time < other
        if isinstance(other, Event):
            return self.time < other.time
        return NotImplemented

    def __ge__(self, other):
        '''if other is a datetime object, does a comparison'''
        if isinstance(other, datetime.datetime):
            return self.time >= other
        if isinstance(other, Event):
            return self.time >= other.time
        return NotImplemented

    def __le__(self, other):
        '''if other is a datetime object, does a comparison'''
        if isinstance(other, datetime.datetime):
            return self.time <= other
        if isinstance(other, Event):
            return self.time <= other.time
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, datetime.datetime):
            return (self.time - other).total_seconds()
        if isinstance(other, Event):
            return (self.time - other.time).total_seconds()
        if isinstance(other, int) or isinstance(other, float):
            return self.time - datetime.timedelta(seconds=other)
        return NotImplemented

    def __add__(self, other):
        if isinstance(other, datetime.datetime):
            return (self.time + other).total_seconds()
        if isinstance(other, event):
            return (self.time + other.time).total_seconds()
        if isinstance(other, int) or isinstance(other, float):
            return self.time + datetime.timedelta(seconds=other)
        return NotImplemented

    def __str__(self):
        '''if other is a datetime object, does a comparison'''
        return self.text

    def __repr__(self):
        return f'{self.text}, time: {self.time}, name: {self.name}'


class Phases():
    '''holds all the phases'''
    def __init__(self, json_obj, events):
        self.phases = [Phase(p, events) for p in json_obj.get('phases', [])]

    def get_next_phase(self, now):
        return min([p for p in self.phases if p > now], default=None)

    def get(self, now):
        '''returns the current phase'''
        return next((phase for phase in self.phases if phase == now), None)


class Phase():
    '''represents a time duration, e.g. totality, partial phases, etc'''
    def __init__(self, dct, events):
        self.text = None
        self.start = None
        self.end = None
        self.load_from_json(dct, events)

    def load_from_json(self, dct, events):
        self.text = dct.get('text', None)
        self.start = events.get_time(dct.get('start', None)) # returns None if it doesn't exist
        self.end = events.get_time(dct.get('end', None)) # returns None if it doesn't exist
        self.time = self.start # so everything has an associated time

    def get(self, now):
        return next((e for e in self.events if e == now), None)

    def __gt__(self, other):
        if isinstance(other, datetime.datetime):
            if self.start is None:
                return False
            if not self.end is None and self.end < other:
                return False
            return self.start > other
        if isinstance(other, Phase):
            return self.start > other.start
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, datetime.datetime):
            if self.end is False:
                return False
            return self.end < other
        if isinstance(other, Phase):
            return self.start < other.start
        return NotImplemented

    def __eq__(self, other):
        if isinstance(other, datetime.datetime):
            if self.start is None or self.start <= other:
                if self.end is None or self.end >= other:
                    return True
            return False
        return NotImplemented

    def __str__(self):
        return self.text

    def __repr__(self):
        return f'<{self.text}, time: {self.time}, start: {self.start}, end: {self.end}>'


class Action():
    '''represents an action, such as a voice or shutter event taken at a given time or for a given duration'''
    def __init__(self, dct, events, get_now):
        self.time = None
        self.start = None
        self.end = None
        self.text = None
        self.get_now = get_now # give access to parent method
        self.allowable = True # whether the action is allowed to be dispatched
        self.load_from_json(dct, events) # creates the action object from the json and events, filling the params above

    def load_from_json(self, dct, events):
        '''loads an event from the json, parsing times and setting values'''
        # determine time
        if 'time' in dct.keys():
            self.time = self.parse_time(dct.get('time'), events) + datetime.timedelta(seconds=float(dct['offset'])) if 'time' in dct and 'offset' in dct else self.parse_time(dct.get('time'), events)
        # save start and end events w/ offsets
        start = events.get_time(dct.get('start', None))
        self.start = start + datetime.timedelta(seconds=dct.get('start_offset')) if 'start_offset' in dct else start
        if self.time is None and not self.start is None:
            self.time = self.start
        end = events.get_time(dct.get('end', None))
        self.end = end + datetime.timedelta(seconds=dct.get('end_offset')) if 'end_offset' in dct else end
        self.text = dct.get('text', None)
        self.name = dct.get('name', None)
        if self.time is None and not self.start is None:
            self.time = self.start

    def parse_time(self, tm, events):
        '''returns a datetime associated with the given tm string, could be an event (like "c2") or a normal datetime object
            uses tzinfo from the events object'''
        if tm in (e.name for e in events.get_events()):
            return next((e.time for e in events.get_events() if e.name == tm), None)
        try:
            return parser.parse(tm, default=datetime.datetime.now()).replace(tzinfo=events.tzinfo)
        except ValueError:
            raise Exception(f'unable to parse: {tm}')

    def __eq__(self, other):
        '''if the current time is within a second of the input datetime, or passed, return True'''
        if isinstance(other, datetime.datetime):
            if not self.time is None:
                if self - other<= 0 and self - other > -1:
                    return True
                return False
            if not self.start is None and not self.end is None: # event with a start and end time
                if other >= self.start and other <= self.end:
                    return True
                return False
        return NotImplemented

    def __gt__(self, other):
        '''if other is a datetime object, does a comparison'''
        if isinstance(other, datetime.datetime):
            return self.time > other
        if isinstance(other, Event) or isinstance(other, Action) or isinstance(other, Phase):
            return self.time > other.time
        return NotImplemented

    def __lt__(self, other):
        '''if other is a datetime object, does a comparison'''
        if isinstance(other, datetime.datetime):
            return self.time < other
        if isinstance(other, Event) or isinstance(other, Action) or isinstance(other, Phase):
            return self.time < other.time
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, datetime.datetime):
            return self.time >= other
        if isinstance(other, Event) or isinstance(other, Action) or isinstance(other, Phase):
            return self.time >= other.time
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, datetime.datetime):
            return self.time <= other
        if isinstance(other, Event) or isinstance(other, Action) or isinstance(other, Phase):
            return self.time <= other.time
        return NotImplemented

    def __add__(self, other):
        if isinstance(other, datetime.datetime):
            return (self.time + other).total_seconds()
        if isinstance(other, Action):
            return (self.time + other.time).total_seconds()
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, datetime.datetime):
            return (self.time - other).total_seconds()
        if isinstance(other, Event) or isinstance(other, Action) or isinstance(other, Phase):
            return (self.time - other.time).total_seconds()
        return NotImplemented

    def __str__(self):
        return self.text

    def __repr__(self):
        return f'<{self.text}, time: {self.time}, start: {self.start}, end: {self.end}, name: {self.name}>'


class VoiceActions():
    '''holds voice action objects'''
    def __init__(self, json_obj, events, get_now):
        '''create a list of voice action objects from the json and save it to the instance'''
        self.actions = [VoiceAction(va, events, get_now) for va in json_obj.get('voice_actions', {})]
        self.get_now = get_now

    def get_next_action(self, now):
        return min([a for a in self.actions if a > now], default=None)

    def get(self, now):
        '''gets any current voice action, returns it, and removes it from the list'''
        submitting = [a for a in self.actions if a == now]
        self.actions = [a for a in self.actions if a not in submitting]
        return submitting


class VoiceAction(Action):
    '''class for a voice action, inherits from Action class'''
    def __init__(self, dct, events, get_now):
        super().__init__(dct, events, get_now)
        self.voice = dct.get('voice', None)

    def play(self):
        text = self.text
        say(text, voice=self.voice)


class CameraActions():
    '''holds camera action objects'''
    def __init__(self, dct, events, get_now):
        '''create a list of camera action objects from the json and save it to the instance'''
        self.get_now = get_now
        self.actions = [CameraAction(ca, events, get_now) for ca in dct.get('camera_actions', {})]

    def get_next_action(self, now):
        return min([a for a in self.actions if a > now], default=None)

    def get_next_n_actions(self, now, n):
        future_actions = sorted([a for a in self.actions if a.time > now], key=lambda a: a.time)
        return future_actions[:n]

    def get(self, now):
        '''gets any current camera action (doesn't remove them like voice actions)'''
        return [ca for ca in self.actions if ca == now]

    def get_allowable(self, now):
        '''gets any current camera action that isn't currently being processed'''
        return [ca for ca in self.actions if ca == now and ca.allowable == True]

    def get_current(self, now):
        '''only used to show actions in the current panel, to include jobs intermittently submitted'''
        return [ca for ca in self.actions if ca.is_current(now)]

class CameraAction(Action):
    '''class for a camera action, (represent a desired photograph, shutter duration, or action with associated timings)'''
    def __init__(self, dct, events, get_now):
        super().__init__(dct, events, get_now)
        self.last_took_photo = None
        self.parse_additional_info(dct, events)

    def parse_additional_info(self, dct, events):
        '''parses out additional metadata in the json'''
        self.interval = dct.get('interval', None)
        self.shutter = dct.get('shutter', None)
        self.priority = dct.get('priority', 0)
        self.camera_id = dct.get('camera_id', None)
        logging.info(f'Parsed Camera Action w/ time: {self.time}, end: {self.end}, start: {self.start}, interval: {self.interval}, shutter: {self.shutter}, camera_id: {self.camera_id}')

    def is_active(self):
        '''returns True or False if the action should currently be running'''
        return self == self.get_now()

    def time_until(self):
        '''time (in sec) left until the camera action is initiated'''
        return (self.time - self.get_now()).total_seconds()

    def time_left(self):
        '''time left (in sec) before the camera action is finished'''
        if self.end:
            return (self.end - self.get_now()).total_seconds()
        return (self.get_now() - self.time).total_seconds() + 1

    def is_continuous(self):
        '''returns True if it is an action that occurs over an interval (with multiple potential shutter presses)
        and returns False if it's a single trigger action that can be executed and then exited'''
        if not self.interval is None:
            return False
        if self.start is None or self.end is None or self.start == self.end:
            return False
        return True

    def duration(self):
        '''returns the duration of the event in seconds'''
        if not self.start and not self.end:
            return 1
        if self.start and self.end:
            return (self.end - self.start).total_seconds()
        return None

    def is_current(self, now):
        '''returns True if action is between the start/end. used for panel'''
        if now < self.time:
            return False
        if self.time and self.start is None and self.end is None:
            dt = (self.time - now).total_seconds()
            return dt <= 0 and dt >= -1
        if now >= self.start and now < self.end:
            return True
        return False

    def __eq__(self, other):
        '''evaluate if the current action should be running given the comparison datetime obj'''
        if isinstance(other, datetime.datetime):
            # Handle the case when self.time is specified, and start/end are not
            if self.time and self.start is None and self.end is None:
                dt = (self.time - other).total_seconds()
                return dt <= 0 and dt >= -1
            # When self.start and self.end are defined
            if self.start and self.end:
                if self.interval:
                    # Check if 'other' is within the start and end times and aligns with the interval
                    if self.start <= other < self.end:
                        return (other - self.start).total_seconds() % self.interval < 1
                else:
                    # Just check if 'other' is within the start and end times
                    return self.start <= other < self.end
            # Handle cases where start or end could be None, considering interval
            if self.interval:
                if self.start and not self.end:
                    if other >= self.start:
                        return (other - self.start).total_seconds() % self.interval < 1
                    return False
                elif self.end and not self.start:
                    if other <= self.end:
                        return (other - datetime.datetime.min).total_seconds() % self.interval < 1
                    return False
            # Handle cases where start or end is None, without interval
            if self.start and not self.end:
                return other >= self.start # implicitly there is no end
            elif self.end and not self.start:
                return other < self.end # implicitly it has already started
            return False
        return NotImplemented


class CameraDispatch():
    '''instantiates and controls one or multiple cameras, dispatching appropriate jobs
    for each camera to it's own queue'''
    def __init__(self, json_obj):
        self.cameras = {} # holds camera objects, their key is the id, object is value
        self.queues = {}
        self.locks = {}
        self.threads = []
        self.parse_camera_info(json_obj) # parse the json to determine which cameras to instantiate
        logging.info('initialized camera keys: {}'.format(self.cameras.keys()))
        logging.info('initialized threads: {}'.format(self.threads))
        logging.info('initialized queues: {}'.format(self.queues))
        logging.info('initialized locks: {}'.format(self.locks))
        logging.info('initialized threads: {}'.format(self.threads))

    def parse_camera_info(self, json_obj):
        '''parses the equipment json, doing initial validation and instantiating camera objects'''
        camera_lst = json_obj.get('equipment')
        if len(camera_lst) < 1:
            logging.error('No camera objects given in .json file!')
            raise Exception('No camera objects given in .json file!')
        for camera_dct in camera_lst:
            camera_id = camera_dct.get('camera_id', None)
            if camera_id in self.cameras.keys():
                logging.error('Multiple Cameras must each be given a unique camera_id!')
                raise Exception('Multiple Cameras must each be given a unique camera_id!')
            self.cameras[camera_id] = Camera(camera_dct) # instantiates the camera
            self.queues[camera_id] = queue.Queue()
            queue_name = '{} Camera Queue'.format(camera_id)
            self.locks[camera_id] = threading.Lock() # create locks for sequential access to shared resources
            # start the thread
            thread = threading.Thread(target=process_queue, args=(self.queues[camera_id],self.locks[camera_id]), name=queue_name)
            thread.start()
            self.threads.append(thread)

    def get_camera_id(self, action):
        camera_ids = self.cameras.keys()
        if len(camera_ids) == 1:
            return next(iter(self.cameras.keys()))
        if action.camera_id not in self.cameras.keys():
            raise Exception('action has camera_id: {}, which is not among camera_ids: {}'.format(action.camera_id, self.cameras.keys()))
        return action.camera_id

    def dispatch_action(self, action):
        cam_id = self.get_camera_id(action)
        if cam_id in self.cameras:
            camera = self.cameras[cam_id]
            logging.info(f"Dispatching action {action} to camera {cam_id}")
            action.allowable = False
            self.queues[cam_id].put((camera.process_action, action))
        else:
            logging.warning(f"Camera ID {cam_id} not found among cameras")

    def complete(self):
        '''when finished, wait for all tasks to end and exit'''
        for q in self.queues.values():
            q.put(None)
        for thread in self.threads:
            thread.join()


def process_queue(q, lock):
    while True:
        task = q.get()
        if task is None:
            q.task_done()
            break
        func, action = task
        with lock:
            logging.info(f"Executing action {action} with function {func}")
            func(action)
        q.task_done()


class Camera():
    '''controls a single camera'''
    def __init__(self, dct):
        self.camera_id = None
        self.f_ratio = None
        self.iso = None
        self.enhancement_factor = None
        self.current_shutter = None # what the shutter speed is set to
        self.currently_active = None # whether it's currently taking a picture
        self.shutter_timeout = 10 # max number of seconds to attempt shutter change continuing to take photos
        self.parse_info(dct) # fills out iso/f_ratio/enhancement factor/camera_id
        self.test_ports() # validate ports
        self.set_mode() # sets mode to save to card on camera

    def parse_info(self, dct):
        # dct is the camera dct from equipment json
        self.camera_id = dct.get('camera_id', None)
        self.serial_port = dct.get('serial_port', None)
        self.usb_port = dct.get('usb_port', None)
        self.f_ratio = float(dct.get('f_ratio', 10))
        self.iso = float(dct.get('iso', 100))
        self.enhancement_factor = float(dct.get('enhancement_factor', 1.0))
        self.shutter_timeout = float(dct.get('shutter_timeout', 10))
        
    def test_ports(self):
        '''attempts to validate/test usb and serial ports for camera'''
        # test serial port
        serial_port = self.serial_port
        usb_port = self.usb_port
        if not serial_port is None and not os.path.exists(serial_port):
            found_serial_ports = glob.glob('/dev/tty*serial*')
            logging.info('found serial ports: {}'.format(found_serial_ports))
            if len(found_serial_ports) == 1:
                logging.warning(f'given serial port not found: "{serial_port}", but found: {found_serial_ports[0]} assigning to camera: {self.camera_id} this may be incorrect w/ multiple cameras.')
                self.serial_port = found_serial_ports[0]
            elif len(found_serial_ports) > 1:
                ports = ', or '.join(found_serial_ports)
                logging.error(f'unable to identify serial port: "{serial_port}", did you mean: "{ports}"?')
                raise Exception(f'unable to identify serial port: "{serial_port}", did you mean: "{ports}"?')
            #logging.error(f'serial port not found: {serial_port}')
            #raise Exception(f'serial port not found: {serial_port}')
        # test usb port
        cam_dct = query_for_usb_cameras() # camera/usb port pairs
        if not usb_port is None and not usb_port in cam_dct.values():
            raise Exception('usb port not found: {}'.format(usb_port))
            logging.error('usb port not found: {}'.format(usb_port))
        if usb_port is None:
            # if the camera id matches the gphoto2 id, use the appropriate port
            if self.camera_id in cam_dct.keys():
                self.usb_port = cam_dct.get(self.camera_id, None)
                logging.info(f'found matching usb camera id: {self.camera_id} with port: {self.usb_port}')
            elif len(cam_dct) < 1:
                logging.warning('No USB camera found!')
                warnings.warn('No USB camera found!')

    def set_mode(self):
        '''sets camera to save to memory card (some default modes will attempt to save to computer, resulting in lost data)'''
        logging.info(f'Setting camera mode to capturetarget=1 (saves image to camera)')
        try:
            if self.usb_port is None:
                result = subprocess.run(['gphoto2', '--set-config', 'capturetarget=1'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            else:
                result = subprocess.run(['gphoto2', f'--port={self.usb_port}',  '--set-config', 'capturetarget=1'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            # Check if the command was successful
            if result.returncode == 0:
                logging.info(f'setting camera mode was successful.')
                return True
        except Exception as e:
            logging.warning(f'Exception encountered when setting camera mode to capturetarget=1 with {e}')
        logging.warning('Failed setting camera mode to capturetarget=1')
        return False


    def use_serial(self):
        '''returns True or False if the camera is set to use the serial port for taking pictures'''
        if self.serial_port is None:
            return False
        return True

    # initiate actions/shutter/shutterspeed changes
    def process_action(self, action):
        '''initiate the action'''
        logging.info(f"Processing action {action} in camera {self.camera_id}")
        self.currently_active = True
        self.set_shutter(action) # determine and set the requisite shutter speed if necessary
        self.take_photo(action) # take the photo for as long a required
        action.allowable = True # make the action allowable again
        self.currently_active = False

    def take_photo(self, action):
        '''takes the photo, for whatever requisite duration, using the usb or serial connection'''
        if action.is_continuous():
            if self.use_serial():
                serial_continuous_capture(action, port=self.serial_port, baud=9600, timeout=None)
            else:
                usb_continuous_capture(action, port=self.usb_port, interval=0)
        else:
            # take a single photo
            if self.use_serial():
                serial_trigger_shutter_once(self.serial_port, interval=0.1, timeout=0.1) 
            else:
                usb_trigger_shutter_once(port=self.usb_port)

    def determine_shutter(self, action):
        if action.shutter in allowable_shutters:
            desired_shutter = action.shutter
        elif action.shutter in allowable_targets:
            desired_shutter = get_shutter_speed(action.shutter, self.f_ratio, self.iso, self.enhancement_factor) # calculates the shutter
        else:
            desired_shutter = action.shutter # attempt to use whatever is given, even if potentially invalid
        return desired_shutter

    def set_shutter(self, action):
        '''attempts to set the shutter, return True if successful, False if Failure'''
        desired_shutter = self.determine_shutter(action)
        if desired_shutter == self.current_shutter:
            return True
        success = set_camera_shutter_speed(desired_shutter, usb_port=self.usb_port, timeout=self.shutter_timeout)
        if success is True:
            self.current_shutter = desired_shutter
        return success

def serial_trigger_shutter_once(port, baud=9600, interval=0.2, timeout=0.1):
    logging.info(f'taking single photo using serial port: {port}, baud: {baud}, interval: {interval}, timeout: {timeout}')
    with serial.Serial(port, baud, timeout=timeout) as ser:
        ser.rts = True
        time.sleep(interval)
    ser.close()
    logging.info(f'completed single photo using serial port: {port}, baud: {baud}, interval: {interval}, timeout: {timeout}')
    time.sleep(1.0) # keeps from multiple triggers during the same second

def usb_trigger_shutter_once(port=None):
    '''triggers the shutter via usb (much slower than serial)'''
    logging.info(f'taking single photo using usb port: {port}')
    try:
        if port is None:
            result = subprocess.run(['gphoto2', '--capture-image'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        else:
            result = subprocess.run(['gphoto2', '--port', port, '--capture-image'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

        # Check if the command was successful
        if result.returncode == 0:
            return True
        else:
            if port is None:
                logging.warning('Failed to take usb photo!: {}'.format(result.stderr))
                warnings.warn('Failed to take usb photo!: {}'.format(result.stderr))
            else:
                logging.warning('Failed to take usb photo on port: {}!: {}'.format(port, result.stderr))
                warnings.warn('Failed to take usb photo on port: {}!: {}'.format(port, result.stderr))
            print(result.stderr)
    except Exception as e:
        logging.warning(f'An error occurred while attempting to take photo over usb: {e}')
        warnings.warn(f'An error occurred while attempting to take photo over usb: {e}')

def serial_continuous_capture(action, port='/dev/tty.usbserial-10', baud=9600, timeout=None):
    # Open the serial port
    logging.info(f'Initiating continuous photo using serial on port: {port}, baud: {baud}, timeout: {timeout}')
    with serial.Serial(port, baud, timeout=timeout) as ser:
        ser.rts = True # Send the "ON" command to trigger the shutter
        while action.is_active(): # Wait for the desired duration of the shutter press
            time.sleep(0.1) # to keep from spamming time check
        ser.rts = False
        ser.close()
    logging.info(f'Completed continuous photo')

def usb_continuous_capture(action, port=None, interval=0):
    '''takes photos continuously until the action is over'''
    while action.is_active():
        if port is None:
            result = subprocess.run(['gphoto2', '--capture-image'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        else:
            result = subprocess.run(['gphoto2', '--port', port, '--capture-image'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        if not result.returncode == 0:
            warnings.warn('Issue with taking photo via usb: {}'.format(result.stderr))
        time.sleep(interval)  # Wait before taking the next photo

def set_camera_shutter_speed(shutter_speed, usb_port=None, timeout=5):
    start_time = time.time()  # Capture the start time
    while True:
        # Check if the current time has exceeded the start time by the timeout duration
        if time.time() - start_time > timeout:
            logging.warning('Timeout exceeded while trying to set shutter speed.')
            warnings.warn('Timeout exceeded while trying to set shutter speed.')
            return False
        try:
            if usb_port is None:
                command = ['gphoto2', '--set-config', f'shutterspeed={shutter_speed}']
            else:
                command = ['gphoto2', '--port', usb_port, '--set-config', f'shutterspeed={shutter_speed}']
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            # Check if the command was successful
            if result.returncode == 0:
                return True
            time.sleep(0.01)
        except Exception as e:
            logging.critical(f'An exception occurred: {e}')
            warnings.warn(f'An exception occurred: {e}')
            return False

def query_for_usb_cameras():
    '''returns a dict of camera: usb_port pairs'''
    p = subprocess.run(['gphoto2', '--auto-detect'], stdout=subprocess.PIPE, universal_newlines=True)
    if p.returncode == 0:
        r = re.compile(r'^(.*?)   +(usb:\S*)\s', re.MULTILINE)
        matches = r.findall(p.stdout)
        cameras = {model: usb for model, usb in matches}
        return cameras
    logging.info('Found usb cameras: {}'.format(cameras))
    return {}

def print_datetime_info(dt):
    if dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None:
        print(f"Timezone-aware: {dt} with timezone {dt.tzinfo}")
    else:
        print(f"Timezone-naive: {dt}")

def progressbar(num, length=100, max_sec=300, text_left=True):
    sec_str = f'{int(num)}'
    sec = rich.text.Text('(', style='green') + rich.text.Text(sec_str, style='cyan') + rich.text.Text(')', style='green')
    if num <= 0:
        return sec #rich.text.Text(' ' * (length- len(sec_str) + 2), style="red")
    if num >= max_sec:
        bar = rich.text.Text('#' * (length - len(sec_str) + 2), style="green")
        if text_left:
            return sec + bar
        return bar + sec
    filled_length = int((num / max_sec) * length) + len(sec_str) + 2
    empty_length = length - filled_length
    
    #bar = rich.text.Text('#' * filled_length, style='green') + rich.text.Text(' ' * empty_length, style="on black")
    if text_left is True:
        return sec + rich.text.Text('#' * filled_length, style='green') + rich.text.Text(' ' * empty_length, style="on black")
    return rich.text.Text(' ' * empty_length, style="on black") + rich.text.Text('#' * filled_length, style='green') + sec

def render_solid(text):
    return pyfiglet.Figlet(font="banner").renderText(text).replace("#", "█")

def format_time(tim):
    if tim is None:
        return '-'
    return tim.strftime('%H:%M:%S %p %Z')

def format_hms(start, end):
    if start is None or end is None:
        return '-'
    if isinstance(start, (Event, Action, Phase)):
        start = start.time
    if isinstance(end, (Event, Action, Phase)):
        end = end.time
    diff = end - start
    days = diff.days
    seconds = diff.seconds
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    mparts = []
    if days > 0:
        parts.append(f"{days}")
    if hours > 0 or (days > 0 and minutes > 0):
        parts.append(f"{hours}")
    if minutes > 0 or (hours > 0 and seconds > 0):
        parts.append(f"{minutes}")
    if minutes == 0 and hours == 0 and days == 0:
        formatted_time = f"{seconds}"
    else:
        parts.append(f"{seconds}".zfill(2))
        formatted_time = ':'.join(parts)
    return formatted_time

def format_timedelta(start, end):
    if start is None or end is None:
        return '-'
    if isinstance(start, Event) or isinstance(start, Action) or isinstance(start, Phase):
        start = start.time
    if isinstance(end, Event) or isinstance(end, Action) or isinstance(end, Phase):
        end = end.time
    # Calculate the difference between the two datetime objects
    diff = end - start
    # Break down the difference into days, seconds, and microseconds
    days = diff.days
    seconds = diff.seconds
    # Calculate hours, minutes, and seconds from the total seconds
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    # Build the output string dynamically based on the values
    parts = []
    if days > 0:
        parts.append(f"{days} day{'s' if days > 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
    if seconds > 0:
        parts.append(f"{seconds} second{'s' if seconds > 1 else ''}")
    # Join the parts with commas and 'and' appropriately
    if len(parts) > 1:
        formatted_time = ', '.join(parts[:-1]) + f', and {parts[-1]}'
    elif parts:
        formatted_time = parts[0]
    else:
        formatted_time = "0 seconds"
    # Return the final string
    return f"{formatted_time}"

def say(text, voice=None):
    logging.info(f'saying "{text}"')
    if voice is None:
        command = 'say -r 184 "{}"'.format(text)
    else:
        command = 'say -r 184 -v {} "{}"'.format(voice, text)
    def target():
        subprocess.run(command, shell=True)
    thread = threading.Thread(target=target)
    thread.start()

def get_Q(target):
    '''get's the brightness exponent Q for the given target'''
    qmap = {'Partial, ND 4.0': 11, 'Partial, ND 5.0': 8, 'Baily\'s Beads': 12, 'Chromosphere': 11, 'Prominences': 9, 'Corona - 0.1 Rs': 7,
        'Corona - 0.2 Rs': 5, 'Corona - 0.5 Rs': 3, 'Corona - 1.0 Rs': 1, 'Corona - 2.0 Rs': 0, 'Corona - 4.0 Rs': -1, 'Corona - 8.0 Rs': -3}
    return qmap.get(target, 11)

def get_shutter_speed(target, f_ratio, iso, enhancement_factor):
    '''returns the appropriate shutter speed string to send to the camera for the given phase
    using the equation referenced @ https://umbra.nascom.nasa.gov/eclipse/980226/tables/table_26.html
    E = our enhancement Factor, so we can scale based on conditions/requirements
    Q = brightness exponent
    '''
    Q = get_Q(target)
    t = enhancement_factor * f_ratio**2 / (iso * 2**Q) # float time for shutter speed
    shutter_string = shutters[min(shutters, key=lambda k: abs(k - t))] # determines the shutter string to return, based on the time (picks the nearest)
    return shutter_string

def argparser():
    '''
    Construct a parser to parse arguments, returns the parser
    '''
    parse = argparse.ArgumentParser(description="Run Eclipse Automator for controlling USB and Serial Cameras")
    parse.add_argument('--input', type=str, default='info.json', help="Path to the JSON config file. Default is 'info.json'.")    
    parse.add_argument('--test',required=False, default=None, type=int, metavar='X', help='Initiate a test run X seconds (positive or negative) from c2 (start of totality)')
    parse.add_argument("--nodisplay", action='store_true', default=False, help="runs without the graphical display")
    parse.add_argument("--nosound", action='store_true', default=False, help="runs without sound alerts")
    parse.add_argument("--noinput", action='store_true', default=False, help="runs without keyboard input")
    parse.add_argument("--verbose", action='store_true', default=False, help="verbose mode")

    return parse


if __name__ == '__main__':
    args = argparser().parse_args() # parse input arguments
    if args.nodisplay is False:
        import rich
        import rich.console
        import rich.layout
        import rich.align
        import rich.panel
        import rich.live
        import pyfiglet
    if args.noinput is False:
        from pynput import keyboard 
    e = EclipseAutomation(test=args.test, inputfile=args.input, nodisplay=args.nodisplay, nosound=args.nosound, noinput=args.noinput, verbose=args.verbose) # instantiate our main objects and run main loop
    
