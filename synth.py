# Imports
import sys
import time
import threading
import numpy as np
import sounddevice as sd
import mido

# Sample Rate in Hz
SAMPLE_RATE = 44100
# Frames per callback
BLOCK_SIZE = 256
# -3 dBFS ceiling (scaled further by velocity)
AMPLITUDE = 0.708

# In seconds
ATTACK_TIME = 0.010
RELEASE_TIME = 0.010

# Semitones
TRANSPOSE = 0

PULSE_WIDTH = 0.5

# One-pole low-pass coefficient [0.0 – 1.0]
LP_CUTOFF = 0.15

# Constants derived from the other constants
ATTACK_SAMPLES = max(1, int(ATTACK_TIME  * SAMPLE_RATE))
RELEASE_SAMPLES = max(1, int(RELEASE_TIME * SAMPLE_RATE))

# Shared synth state
lock = threading.Lock()

state = {
    "note": None,
    # frequency after transpose
    "freq": 0.0,
    "velocity_amp": 1.0,
    # oscillator phase accumulator [0, 1)
    "phase": 0.0,
    # one-pole filter state
    "lp_z": 0.0,
    # attack, sustain, release, or idle
    "env_stage": "idle",
    # counter
    "env_pos": 0,
    # current envelope amp [0, 1]
    "env_level": 0.0,
    "pending_note": None,
}

def midi_note_to_freq(note: int) -> float:
    # MIDI note to Hz, with transpose
    return 432.0 * 2.0 ** ((note - 69 + TRANSPOSE) / 12.0)

def audio_callback(outdata: np.ndarray, frames: int, time_info, status):
    if status:
        print(f"[audio] {status}", file=sys.stderr)

    output = np.zeros(frames, dtype=np.float32)

    with lock:
        pending = state["pending_note"]
        if pending is not None:
            state["pending_note"] = None
            action, note, vel = pending

            if action == "on":
                state["note"] = note
                state["freq"] = midi_note_to_freq(note)
                state["velocity_amp"] = vel / 127.0
                state["env_stage"] = "attack"
                state["env_pos"] = 0
            else:
                if state["note"] == note and state["env_stage"] != "idle":
                    state["env_stage"] = "release"
                    state["env_pos"] = 0

        # Local copies of hot state
        phase = state["phase"]
        lp_z = state["lp_z"]
        freq = state["freq"]
        vel_amp = state["velocity_amp"]
        stage = state["env_stage"]
        pos = state["env_pos"]
        level = state["env_level"]

        if stage != "idle" and freq > 0.0:
            phase_inc = freq / SAMPLE_RATE

            for i in range(frames):
                # AR envelope
                if stage == "attack":
                    level += 1.0 / ATTACK_SAMPLES
                    pos += 1
                    if level >= 1.0:
                        level = 1.0
                        stage = "sustain"
                        pos = 0

                elif stage == "sustain":
                    level = 1.0

                elif stage == "release":
                    level -= 1.0 / RELEASE_SAMPLES
                    pos += 1
                    if level <= 0.0:
                        level = 0.0
                        stage = "idle"
                        pos = 0

                # Pulse oscillator
                if phase < PULSE_WIDTH:
                    raw = 1.0 
                else:
                    raw = -1.0

                # One-pole low-pass filter
                lp_z = lp_z + LP_CUTOFF * (raw - lp_z)

                output[i] = np.float32(lp_z * level * vel_amp * AMPLITUDE)

                phase += phase_inc
                if phase >= 1.0:
                    phase -= 1.0

        state["phase"] = phase
        state["lp_z"] = lp_z
        state["env_stage"] = stage
        state["env_pos"] = pos
        state["env_level"] = level

    outdata[:] = output.reshape(-1, 1)

def handle_midi_message(msg):
    # Key on
    if msg.type == "note_on":
        # If 0 velocity, then it's treated as key off
        if msg.velocity == 0:
            with lock:
                state["pending_note"] = ("off", msg.note, 0)
        # Else it's still treated as key on
        else:
            with lock:
                state["pending_note"] = ("on", msg.note, msg.velocity)
    # Key off
    elif msg.type == "note_off":
        with lock:
            state["pending_note"] = ("off", msg.note, msg.velocity)

def choose_midi_port() -> str:
    ports = mido.get_input_names()
    if not ports:
        sys.exit("No MIDI input ports found.\nMake sure python-rtmidi is installed and a controller is fully connected.")

    # To auto-connect to my MIDI controller and subsequently other mpd218 controllers
    for name in ports:
        if "mpd218" in name.lower() or "mpd 218" in name.lower():
            print(f"Auto-selected MIDI port: {name}")
            return name

    # Otherwise list the available ports
    print("Available MIDI input ports:")
    for i, name in enumerate(ports):
        print(f" [{i}] {name}")
    while True:
        try:
            idx = int(input("Select port number: "))
            return ports[idx]
        except (ValueError, IndexError):
            print("Invalid choice, please try again and enter just the number.")

def main():
    print(f"\nCurrent configuration:\n Transpose: {TRANSPOSE:+d} semitones")
    print(f" Pulse width: {PULSE_WIDTH:.2f}\n LP cutoff: {LP_CUTOFF:.3f}\n")

    port_name = choose_midi_port()

    print(f"\n(SR = {SAMPLE_RATE} Hz, block = {BLOCK_SIZE} frames / {1000*BLOCK_SIZE/SAMPLE_RATE:.1f} ms)")
    print("Press Ctrl-C to quit.\n")

    with sd.OutputStream(
            samplerate = SAMPLE_RATE,
            blocksize = BLOCK_SIZE,
            channels = 1,
            dtype = "float32",
            callback = audio_callback,
    ):
        with mido.open_input(port_name, callback=handle_midi_message):
            try:
                while True:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                print("\nStopped.")

if __name__ == "__main__":
    main()