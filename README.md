
# Eclipse Automator

This script offers a sophisticated and lightweight solution for the automated orchestration of eclipse photography. It is designed to control an unlimited number of cameras through both USB and serial connections, and provides full customization of imaging sequences, user-defined voice notifications and a terminal-based graphical user interface (GUI).

The utility enables photographers to manage multiple cameras from a single computer, facilitating separate sophisticated imaging sequences across multiple telescopes or imaging setups, allowing for virtually hands-free operation. Particularly, it supports serial connections, such as those used with Canon cameras, allowing for the capture of significantly more data during the critical period of totality.

Key features include the calculation of optimal exposure times for the specific equipment used, along with the flexibility to adjust global exposure durations in real-time via simple keystrokes, ensuring immediate correction for any issues with under or overexposure. Furthermore, the software allows for the easy integration of custom audio alerts and countdowns.

A simple dashboard presents a overview of active cameras, along with a queue of impending camera actions timings, and eclipse phase timer. This entire process is customizable through a single JSON file. Moreover, the script offers the functionality to run tests of your automation sequences at any chosen starting point via a single command.

In summary, this script simplifies many of the technical complexities of eclipse photography, allowing photographers to capture sophisticated sequences while also being able to enjoy the eclipse itself.

![Example Run](./example.png)

___ 


## Requirements

In running the script, you will need to install the python libraries, and then edit the info.json file to include phase times, your equipment, and desired image sequence and voice notifications (see below for explanation of the json schema). 

Currently, you will need some method to determine your particular eclipse timings given your location. Options include the [Navy Calculator](https://aa.usno.navy.mil/data/SolarEclipses), [Photo Ephemeris](https://app.photoephemeris.com/), and the [Solar Eclipse Timer App](https://www.solareclipsetimer.com/).

You will need a camera and a usb connection. gphoto2 is required for usb camera control. (eg `sudo apt-get install gphoto2` or `brew install gphoto2`) Event audio notifcations are currently only supported by OSX.

___ 

## Installation


Clone and jump into the repository with

```
git clone https://github.com/jlinick/EclipseAutomator.git
cd EclipseAutomator
```

(Optionally) set up a virtual environment
```
python3 -m venv .eclipse
```

Install requisite python packages
```
python3 -m venv .eclipse
pip install -r requirements.txt
```
and you're good to go!

If you installed a virtual environment, you can exit with 
```
deactivate
```

and to load your virtual environment again
```
source .eclipse/bin/activate
```
___ 

## Running

For full customization of timings, cameras, and camera actions, see [below](#editing-info.json).

To test Eclipse Automator, plug in your camera and run
```
./run.py --test -95
```
This starts a test 95 seconds before c2. Simply change the number to change where the test starts. Positive numbers will be after the start of totality, negative numbers will be before it.


To run with or without gui/voice notifications/keyboard input run
```
./run.py --nodisplay --nosound --noinput
```

Or change the input.json file to a different one
```
./run.py --input --test.json
```

On the day of the eclipse simply run
```
./run.py
```


## Schema for info.json

The info jsonfile is structured into a 5 parts: events, equipment, phases, voice_actions, and camera actions. This is where you set timings, and orchestration for all your cameras. You can create several different jsonfiles, and run each with the --input filename.json in the run.py command.

### events

The events list is where you specify the timing of c1, c2, c3, max eclipse, and c4. This should be set to your exact location (we recommend something like the Solar Eclipse Timer App https://www.solareclipsetimer.com/ )
```
"events":[
    {"name": "c1", "time": "2024-04-08 10:16:57.1", "text": "First Contact"},
    {"name": "c2", "time": "2024-04-08 11:34:20.4", "text": "Beginning of Totality"},
    {"name": "max","time": "2024-04-08 11:36:32.1", "text": "Maximum Eclipse"},
    {"name": "c3", "time": "2024-04-08 11:38:43.8", "text": "End of Totality"},
    {"name": "c4", "time": "2024-04-08 12:57:30.3", "text": "End of Eclipse"}
],
```
All of the subsequent events are based on these times, so these need to be entered precisely. *note that all times should be in local time - or in whatever time your computer is set to*

### equipment

This section is where you enter your camera info.
```
"equipment":[
    {"camera_id": "Canon EOS R5", "serial_port": "/dev/tty.usbserial-1130", "f_ratio": 6.3, "iso": 400, "enhancement_factor": 1.0},
    {"camera_id": "Canon EOS 5D Mark II", "f_ratio":1.4, "iso":400, "enhancement_factor": 1.0}
],
```

`camera_id` should uniquely identify your camera, if only one camera is used it is not necessary. We recommend you use the camera name specified by gphoto2 (you can check by running `./show_devices.sh`). This will allow the script to identify the usb port of your equipment regardless if the port is connected to your computer. Otherwise, if you change the port your camera is plugged into you will need to specify the correct port in usb_port below.

`usb_port` (optional) the usb port of the camera. This will show up under /dev/tty\*usb\* Keep in mind if you plug your camera into different ports this will change. Runing `./show_devices.sh` should show you your connected cameras and their specific usb ports.

`serial_port` required to control cameras via a serial port. run `./show_devices.sh` for a list of available serial devices.

`f_ratio` required only when using the script to calculate your exposure times.

`iso` required only when using the script to calculate your exposure times.


`enhancement_factor` recommended when you want one camera to calculate exposure times differently than another. (just a constant scalar. This can be adjusted on the fly with the up and down arrows on the keyboard)

### phases

Unless you decide to add or remove a new event above, you can leave this alone. It's only used to update the text graphic for the given phase.

```
"phases":[
    {"end": "c1", "text": "Pre-Eclipse"},
    {"start": "c1", "end": "c2", "text": "Partial"},
    {"start": "c2", "end": "c3", "text": "Totality"},
    {"start": "c3", "end": "c4", "text": "Partial"},
    {"start": "c4", "text": "Post-Eclipse"}
],
```

### voice_actions

Each voice action represents a specific audio notification given at a specific time. This is where you enter each voice action. Each action is referenced to a specific time (determined by the events above.)

```
{"text": "First phase of the eclipse begins in 20 minutes.", "time": "c1", "offset": -1200, "voice": "Alex"},
```
`text` is the phrase that is spoken

`time` is the phase that is used as a time reference

`offset` (optional) the number of seconds the notification is offset from that event. defaults to 0.

`voice` to use one of the different Apple Voices (there are many) you can include it here.

So to do a countdown to totality, you would add
```
{"text": "Totality in.", "time": "c2", "offset": -6},
{"text": "5.", "time": "c2", "offset": -5},
{"text": "4.", "time": "c2", "offset": -4},
{"text": "3.", "time": "c2", "offset": -3},
{"text": "2.", "time": "c2", "offset": -2},
{"text": "1.", "time": "c2", "offset": -1},
{"text": "Totality has begun!", "time": "c2"}
```

### camera_actions

These can be referenced in the same way as the above, for a single photograph at a specific time, but camera_actions also support photos taken every X intervals, or as many shots of a specific type as possible, over a given period.

`text` is the text shown on the GUI when the event is being run, or queued.

`shutter` is the given shutter speed for that action. The script will calculate shutter times for your equipment if a specific string is input here (see below).

`time`, `start` and `end` are used as a time reference for that event (should be "c1","c2","max","c3","or c4")

`offset` `start_offset` and `end_offset` are used with `time` to offset (in seconds) relative to the given event. it should be a negative or positive integer, negative for before the event, and positive after. This controls when the event starts and ends.


A few examples: 

a single shot, taken 90 seconds before totality:
```
{"text": "Single shot", "shutter": "1/200", "time": "c2", "offset": -90}
```

a series of shots, taken every 20 seconds during the first partial phase:
```
{"text": "Partial Phase Shots", "shutter": "1/2000", "start": "c1", "end": "c2", "interval" 20}
```

a series of shots, taken every 20 seconds during the first partial phase, starting 95 seconds after c1 and ending 30 seconds before c2:
```
{"text": "Partial Phase Shots", "shutter": "1/2000", "start": "c1", "start_offset": 95, "end": "c2", "end_offset": -30, "interval" 20}
```

as many shots as possible, at 1/5000 shutter speed, during the 12 seconds up to c2:
```
{"text": "Baily's Beads", "shutter": "1/5000", "start": "c2", "start_offset": -12, "end": "c2"}
```

if multiple cameras are used, you must include a `camera_id` value for each camera action. So a really simple action of two cameras capturing all of totality with different shutter speeds could be:
```
{"text": "R5 Totality", "shutter": "1/5000", "start": "c2", "end": "c3","camera_id": "Canon EOS R5" },
{"text": "5d Totality", "shutter": "1/250", "start": "c2", "end": "c3", "camera_id": "Canon EOS 5d Mark IV"}
```

Additionally, if any of the strings below are inserted in the `shutter` field, eclipse times are calculated in accordance with [this NASA Exposure Guide](https://umbra.nascom.nasa.gov/eclipse/980226/tables/table_26.html):

```
'Partial, ND 4.0', 'Partial, ND 5.0', 'Baily\'s Beads', 'Chromosphere', 'Prominences', 'Corona - 0.1 Rs','Corona - 0.2 Rs', 'Corona - 0.5 Rs', 'Corona - 1.0 Rs', 'Corona - 2.0 Rs', 'Corona - 4.0 Rs', 'Corona - 8.0 Rs'
```

This all makes for a robust and powerful method for controlling multiple cameras. Here we include an example of a sequence that captures partial phases with a 30 second interval, captures Baily's Beads, brackets up through exposures, captures the Earthshine during max eclipse (when the moon is centered), brackets down through exposures and then captures Baily's beads, transitioning into a photo every 30 seconds during the partial phase.
```
"camera_actions":[
	{"text": "Partial Phase", "shutter": "1/200", "start": "c1", "end":"c2", "end_offset":-14, "interval": 30},
	{"text": "Capturing Baily's Beads", "shutter": "Baily's Beads", "start": "c2", "start_offset": -12, "end":"c2", "end_offset": 6},
	{"text": "Capturing Chromosphere", "shutter": "Chromosphere", "start":"c2", "start_offset":6, "end":"c2", "end_offset":16},
	{"text": "Capturing Prominences", "shutter": "Prominences", "start":"c2", "start_offset":16, "end":"c2", "end_offset":26},
	{"text": "Corona - 0.1 Rs", "shutter": "Corona - 0.1 Rs", "start":"c2", "start_offset":26, "end":"c2", "end_offset":36},
	{"text": "Corona - 0.5 Rs", "shutter": "Corona - 0.5 Rs", "start":"c2", "start_offset":36, "end":"c2", "end_offset":46},
	{"text": "Corona - 1.0 Rs", "shutter": "Corona - 1.0 Rs", "start":"c2", "start_offset":46, "end":"c2", "end_offset":56},
	{"text": "Corona - 2.0 Rs", "shutter": "Corona - 2.0 Rs", "start":"c2", "start_offset":56, "end":"c2", "end_offset":66},
	{"text": "Corona - 4.0 Rs", "shutter": "Corona - 4.0 Rs", "start":"c2", "start_offset":66, "end":"c2", "end_offset":76},
	{"text": "Corona - 8.0 Rs", "shutter": "Corona - 8.0 Rs", "start":"c2", "start_offset":76, "end":"c2", "end_offset":86},
	{"text": "Corona - 0.1 Rs", "shutter": "Corona - 0.1 Rs", "start":"c2", "start_offset":86, "end":"max", "end_offset":-16},
	{"text": "Earthshine", "shutter":"8", "start":"max", "start_offset":-16, "end":"max", "end_offset":16},
	{"text": "Corona - 8.0 Rs", "shutter": "Corona - 8.0 Rs", "start":"max", "start_offset":16, "end":"max", "end_offset":26},
	{"text": "Corona - 4.0 Rs", "shutter": "Corona - 4.0 Rs", "start":"max", "start_offset":26, "end":"max", "end_offset":36},	
	{"text": "Corona - 2.0 Rs", "shutter": "Corona - 2.0 Rs", "start":"max", "start_offset":36, "end":"max", "end_offset":46},
	{"text": "Corona - 1.0 Rs", "shutter": "Corona - 1.0 Rs", "start":"max", "start_offset":46, "end":"max", "end_offset":56},
	{"text": "Corona - 0.5 Rs", "shutter": "Corona - 0.5 Rs", "start":"max", "start_offset":56, "end":"max", "end_offset":66},
	{"text": "Corona - 0.1 Rs", "shutter": "Corona - 0.1 Rs", "start":"max", "start_offset":66, "end":"max", "end_offset":76},
	{"text": "Capturing Prominences", "shutter": "Prominences", "start":"max", "start_offset":76, "end":"max", "end_offset":86},
	{"text": "Capturing Chromosphere", "shutter": "Chromosphere", "start":"max", "start_offset":86, "end":"c3", "end_offset":0},
	{"text": "Capturing Baily's Beads", "shutter": "Baily's Beads", "start": "c3", "end_offset": 0, "end":"c3", "end_offset": 12},
	{"text": "Partial Phase", "shutter": "1/200", "start": "c3", "end": "c4", "start_offset": 14, "interval":30}
]
```

an example json is included as info.json.

When you are finished editing your jsonfile, run the program with 

```
./run.py --input your_json_file_path
```

___ 

## Troubleshooting


Note that many cameras will go to sleep if connected to a usb port without activity for a set period of time, and therefore will not show up as a connected device. So before running your script, either reset the camera or press the shutter to wake the camera. If the camera is left connected but not used for some time, it may turn off and not recognize usb commands (so we recommend keeping it on an interval). A serial cable connection will still work and should wake the camera in these situations. Currently we recommend you run `show_devices.sh` before you start your script, to make sure usb cameras are connected. Note that if you leave some image editing programs running (like Adobe Lightroom/Photoshop), they will block use of these usb devices, so we recommend closing these programs before use.

Currently the script does not validate the jsonfile. So a typo there will likely cause the script not to run. Make sure your json is formatted properly!

Running the script will generate a run.log logfile, which you should inspect if you run into any issues.

___ 

## Miscellaneous

Future work includes the ability to referece camera actions into sequences, and then run specific sequences in whatever order you like (or as filler, for example). I would also like have an optional query to the [US Navy's API](https://aa.usno.navy.mil/data/api) to set the timings from your location. Neither of these will likely be added before the April 8th, 2024 eclipse- unless, of course, you decide to add them yourself!

For serial cable connections we recommend [Hap Griffin Astrocables](https://imaginginfinity.com/astrocables.htm), or [make your own!](https://www.covingtoninnovations.com/dslr/canonrelease40d.html).


___ 

## Authors

- [@jlinick](https://www.github.com/jlinick)

