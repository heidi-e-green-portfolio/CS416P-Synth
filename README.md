# CS416P-Synth
Heidi Green   
## synth.py    
Monophonic pulse-wave MIDI synthesizer with AR envelope, transpose, velocity-sensitive amplitude, and one-pole low-pass filter. Adjustable constants are listed at the top of the file after all the imports. Custom tuning at 432.0 Hz. Automatically selects MPD218 port if it's available, or otherwise you can select which port to connect to.

## Build Instructions   
**The following libraries need to be installed:**   
numpy  
sounddevice   
mido   
python-rtmidi    

**Can be done so with the following command:**   
pip install -r requirements.txt

## Running   
**The script can be run directly from your terminal with the following command:**   
python synth.py  

## Reflection   
**What I Did:**   
Created a monophonic MIDI synth that listens for a MIDI controller connection. It uses sawtooth waves for the synthesizer sound, with a fixed attack-release volume envelope.

**How It Went:**    
The process went pretty well, and it was fun to experiment with different tunings, transposes, etc. Adding a one-pole low-pass filter was also a fun addition.

**What's Still to be Done:**   
There's definitely a lot of room for this program to be built up more. Right now, it silently ignores other MIDI messages, but having it respond to more would be an interesting addition. 
