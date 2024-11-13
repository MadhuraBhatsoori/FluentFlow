# import libraries and load environmental variables
import pyaudio
import numpy as np
import pymongo
import json
from pymongo import MongoClient
import certifi
import numpy as np
import librosa
import soundfile as sf
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()
connection_string = os.getenv('MONGO_CONNECTION_STRING')
client = MongoClient(connection_string, tlsCAFile=certifi.where())
db = client['audio']
mongodb_sounds_collection = db['sounds']
mongodb_results_collection = db['results']


RECORD_SECONDS = 5
SAMPLE_RATE = 44100
CHUNK_SIZE = 1024


# Normalize and convert audio into embeddings 

def normalize(v):
    norm = np.linalg.norm(v)
    if norm == 0:
        return v
    return v / norm

def get_embedding(audio_data):
    
    input_array = np.array(audio_data, dtype=np.int16)
    scaled_array = np.interp(input_array, (-32768, 32767), (-1, 1))
    features = []

    features.append(np.sqrt(np.mean(np.square(scaled_array))))
    features.append(np.sum(np.abs(np.diff(np.signbit(scaled_array)))) / len(scaled_array))
    spectrum = np.abs(np.fft.fft(scaled_array))
    features.extend([
        np.mean(spectrum),
        np.std(spectrum),
        np.max(spectrum),
    ])
    feature_vector = np.array(features)
    return normalize(feature_vector)

# Insert audio to mongoDB database
def insert_mongo_results(results, mongodb_results_collection):
    entry = {"data_time":datetime.now(),"results":results}
    mongodb_results_collection.insert_one(entry)

def insert_mongo_sounds(audio_name, embedding, audio_file, mongodb_sounds_collection):
    entry = {"audio":audio_name,"emb":embedding,"audio_file":audio_file}
    mongodb_sounds_collection.insert_one(entry)

def knnbeta_search(embedding, mongodb_sounds_collection):
    query_vector = embedding.tolist()
    
    search_query = [
        {
            "$search": {
                "knnBeta": {
                    "vector": query_vector,
                    "path": "emb",
                    "k": 3
                }
            }
        },
        {
            "$project": {
                "_id": 0,
                "audio": 1,
                "image": 1,
                "audio_file": 1,
                "score": { "$meta": "searchScore" }
            }
        }
    ]
    
    results = mongodb_sounds_collection.aggregate(search_query)
    return results

# Get audio from device

p = pyaudio.PyAudio()
info = p.get_host_api_info_by_index(0)
num_devices = info.get('deviceCount')

for i in range(num_devices):
    device_info = p.get_device_info_by_host_api_device_index(0, i)
    if device_info['maxInputChannels'] > 0:
        print(f"Device {i}: {device_info['name']}")

input_device = input("Which input device do you want to use?")

print(input_device)

# Load filler words into database
audio = pyaudio.PyAudio()
audio_description_dictionary = [
    {
        "audio": "Like",
    },
    {
        "audio": "maybe",
    },
    {
        "audio": "i mean", 
    },
    {
        "audio": "literally", 
    },
    {
        "audio": "you know", 
    }
]

# Audio processing for loaded words

for audio_description in audio_description_dictionary:
    input(f"Record '{audio_description['audio']}' - press enter when ready")

    stream = audio.open(format=pyaudio.paInt16, channels=1, rate=SAMPLE_RATE, input=True, frames_per_buffer=CHUNK_SIZE,input_device_index=int(input_device))

    for j in range(1):
        stream.start_stream()
        frames = []
        for i in range(0, int((SAMPLE_RATE / CHUNK_SIZE) * RECORD_SECONDS)):
            data = stream.read(CHUNK_SIZE)
            frames.append(data)

        stream.stop_stream()

        audio_data = np.frombuffer(b"".join(frames), dtype=np.int16)

        emb = get_embedding(audio_data)

        insert_mongo_sounds(f"{audio_description['audio']}", emb.tolist(), f"{j}", mongodb_sounds_collection)
    stream.close()
    print('Recorded successfully')

audio.terminate()