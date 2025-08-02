#!/usr/bin/env python3

import os
import subprocess
import sys
import argparse

# Configuration
dir_path = "/usr/share/asterisk/sounds/en_US_f_Allison/"
tts_engine = "google"  # or "google"
piper_en = "/opt/piper/en_US-amy-medium.onnx"
piper_nl = "/opt/piper/nl-NL-female.onnx"

def sanitize_message(message):
    return message.replace("'", "")

def make_filename(message, long=False):
    if long:
        return "tts-hass-longmessage"
    return "tts-hass-" + message.translate(str.maketrans({':':'_', ',':'_', '/':'_', ' ':'_', '.':'_'}))

def file_exists(filename):
    return os.path.isfile(os.path.join(dir_path, f"{filename}.gsm"))

def run_tts(lang, message, long=False):
    filename = make_filename(message, long)
    full_path = os.path.join(dir_path, f"{filename}.gsm")

    if file_exists(filename) and not long:
        return filename

    message = sanitize_message(message)

    if tts_engine == "google":
        command = f"gtts-cli -l {lang} '{message}' | sox -t mp3 - -r 8000 -c1 {full_path}"
    elif tts_engine == "piper":
        model = piper_nl if lang == "nl" else piper_en
        command = f"echo '{message}' | piper --model {model} --download-dir /opt/piper/ --data-dir /opt/piper/ | sox -t wav - -r 8000 -c1 {full_path}"
    else:
        print("Unsupported TTS engine.")
        return None

    retval = subprocess.call(command, shell=True)
    return filename if retval == 0 else None

def main():
    parser = argparse.ArgumentParser(description="Generate TTS GSM file")
    parser.add_argument("lang", help="Language code (e.g., 'nl', 'en')")
    parser.add_argument("message", help="Message to speak")
    parser.add_argument("--long", action="store_true", help="Use long message mode")
    args = parser.parse_args()

    result = run_tts(args.lang, args.message, args.long)
    if result:
        print(result)
    else:
        sys.exit("Error generating speech")

if __name__ == "__main__":
    main()
