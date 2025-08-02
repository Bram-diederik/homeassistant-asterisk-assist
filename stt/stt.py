#!/usr/bin/env python3
import asyncio
import re
import os
import sys
import yaml
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.asr import Transcribe
from wyoming.client import AsyncTcpClient

CONFIG_FILE = "/opt/sascha/whisper/whisper_servers.yaml"

def load_server(lang):
    try:
        with open(CONFIG_FILE, "r") as f:
            config = yaml.safe_load(f)
        server = config["servers"].get(lang)
        if not server:
            raise ValueError(f"No server config for language: {lang}")
        return server["host"], server["port"]
    except Exception as e:
        print(f"Error reading config: {e}", file=sys.stderr)
        sys.exit(1)

async def transcribe_wav(wav_path: str, host: str, port: int, lang: str):
    lang = re.sub(r'-[^_]+$', '', lang)
    try:
        async with AsyncTcpClient(host, port) as client:
            await client.write_event(Transcribe(language=lang).event())

            with open(wav_path, "rb") as f:
                await client.write_event(AudioStart(rate=16000, width=2, channels=1).event())
                while True:
                    chunk = f.read(1024)
                    if not chunk:
                        break
                    await client.write_event(AudioChunk(rate=16000, width=2, channels=1, audio=chunk).event())
                await client.write_event(AudioStop().event())

            while True:
                event = await client.read_event()
                if event is None:
                    return None
                if event.type == "transcript":
                    return event.data["text"]
    except Exception as e:
        print(f"Error transcribing {wav_path}: {str(e)}", file=sys.stderr)
        return None

def convert_to_wav(input_path, output_path):
    ret = os.system(
        f"ffmpeg -y -i {input_path} -ar 16000 -ac 1 -c:a pcm_s16le {output_path} >/dev/null 2>&1"
    )
    return ret == 0

if __name__ == "__main__":
    if len(sys.argv) != 5 or sys.argv[1] != "--lang":
        print(f"Usage: {sys.argv[0]} --lang <lang> <wav_file> <output_file>", file=sys.stderr)
        sys.exit(1)

    lang = sys.argv[2]
    input_file = sys.argv[3]
    output_file = sys.argv[4]

    if not os.path.exists(input_file):
        print(f"Input file {input_file} does not exist", file=sys.stderr)
        sys.exit(1)

    wav_file = f"{input_file}.converted.wav"

    host, port = load_server(lang)

    if not convert_to_wav(input_file, wav_file):
        print("WAV conversion failed", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(wav_file):
        print(f"Converted file {wav_file} not found", file=sys.stderr)
        sys.exit(1)

    transcription = asyncio.run(transcribe_wav(wav_file, host, port, lang))

    if transcription:
        with open(output_file, "w") as f:
            f.write(transcription)
        print(f"Successfully transcribed to {output_file}")
    else:
        print("Transcription failed", file=sys.stderr)
        sys.exit(1)

    try:
        os.remove(wav_file)
    except OSError as e:
        print(f"Error removing temporary file: {str(e)}", file=sys.stderr)
