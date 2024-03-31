
# Eclipse Automator

A simple lightweight script for fully customizable automation of eclipse photography. Controls any number of usb cameras and serial connections, with customizable voice event notifications and a simple terminal GUI.

Being disappointed with the options available for eclipse photography - especially support for serial connections which enable much higher capture rates (such as Hap Griffin Astrocables https://imaginginfinity.com/astrocables.htm), I wrote my own. This assumes you can calculate your exact timings for c1, c2, c3, and c4 (such as through the Solar Eclipse Timer App https://www.solareclipsetimer.com/) but allows for full customizability of your imaging sessions, with effectively an infinite number of cameras. 

I recommend you run this on OSX if you want voice notifications, but everything else should run on any system.
## Installation

Clone and jump into the repository

```
git clone https://github.com/jlinick/EclipseAutomator.git
cd EclipseAutomator
```

(Optional) set up a virtual environment
```
python3 -m venv .eclipse
```


Install requisite python packages
```
python3 -m venv .eclipse
pip install -r requirements.txt
```


To load your virtual environment again
```
source .eclipse/bin/activate
```
## Documentation

Edit info.json to add timings, cameras, and camera actions (see [below](#editing-info.json) for more info).

Run a test of the Eclipse Automator plug in your camera and run:
```
./run.py --test -95
```
This starts a test 95 seconds before c2, change the number to change where the test starts.


To run with or without gui/voice notifications/input capture
```
./run.py --nodisplay --nosound --noinput
```

Or change the input.json file to a different one
```
./run.py --input --test.json
```

The automator will generate a run.log logfile, which you can inspect for any warnings or if there are any issues.
## Editing info.json

The info jsonfile is structured into a 5 parts events, equipment, phases, voice_actions, and camera actions. This is where you set timings, and orchestration for all your cameras.

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
All of the subsequent events are based on these times, so these need to be entered precisely.

### equipment

This section is where you enter your camera info.
```
"equipment":[
    {"camera_id": "Canon EOS R5", "serial_port": "/dev/tty.usbserial-1130", "f_ratio": 6.3, "iso": 400, "enhancement_factor": 1.0},
    {"camera_id": "Canon EOS 5D Mark II", "f_ratio":1.4, "iso":400, "enhancement_factor": 1.0}
],
```

`camera_id` is the identification of your camera, if only one camera is used it is not necessary. We recommend you use the camera name specified by gphoto2 (you can check by running `./show_devices.sh`). This will allow the script to identify the usb port of the given equipment.
`usb_port` (optional) the usb port of the camera. On macs this will show up under /dev/tty*usb* Keep in mind if you plug your camera into different ports this will change.
`serial_port` required to control cameras via a serial port. run `./show_devices.sh` for a list of available serial devices.
`f_ratio` required only when using the script to calculate your exposure times.
`iso` required only when using the script to calculate your exposure times.
`enhancement_factor` recommended when you want one camera to calculate exposure times differently than another. (just a constant scalar. This can be adjusted on the fly with the up and down arrows)

### phases

Unless you want to add or remove a new phase, you can just leave this alone. It's only used to update the text graphic for the given phase.

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

Each voice action represents a specific voice notification given at a specific time, referenced to a phase as given in the events above.
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
`shutter` is the given shutter speed for that action.
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


This makes for a robust and powerful method for controlling multiple cameras. An example of capturing partial phases with a 30 second interval, then capturing Baily's Beads, bracketing up through exposures, capturing Earthshine, bracketing down through exposures and capturing the exiting Baily's beads, to transition into a Partial Phase 30 second interval is shown below.
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

## Authors

- [@jlinick](https://www.github.com/jlinick)

