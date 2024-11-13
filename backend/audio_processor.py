#import libraries
import pyaudio
import numpy as np
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv
import threading
import time
import sys
import logging
from typing import Optional, List, Dict, Any
import certifi

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AudioProcessor:
    # Connect to mongoDB database
    def __init__(self, sensor_name: str = "default"):
        self.RECORD_SECONDS = 3
        self.SAMPLE_RATE = 44100
        self.CHUNK_SIZE = 1024
        self.running = False
        self.sensor_name = sensor_name
        
        load_dotenv()
        mongo_uri = os.getenv('MONGO_CONNECTION_STRING')
        if not mongo_uri:
            raise ValueError("MongoDB connection string not found in environment variables")

        try:
            self.client = MongoClient(mongo_uri, tlsCAFile=certifi.where())
            self.db = self.client['audio']
            self.sounds_collection = self.db['sounds']
            self.results_collection = self.db['results']
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    # Find default device to record
    def find_default_input_device(self) -> Optional[int]:
        audio = pyaudio.PyAudio()
        try:
            info = audio.get_host_api_info_by_index(0)
            num_devices = info.get('deviceCount')
            
            logger.info("\nAvailable input devices:")
            default_device = None
            
            for i in range(num_devices):
                device_info = audio.get_device_info_by_host_api_device_index(0, i)
                if device_info['maxInputChannels'] > 0:
                    logger.info(f"Device {i}: {device_info['name']}")
                    if default_device is None:
                        default_device = i                        
            if default_device is not None:
                logger.info(f"\nAutomatically selected device {default_device}")
            else:
                logger.error("No input devices found")
                
            return default_device
            
        finally:
            audio.terminate()
    
    # Normalize and convert audio into embedding
    def normalize(self, v):
        norm = np.linalg.norm(v)
        if norm == 0:
            return v
        return v / norm

    def get_audio_embedding(self, audio_data):
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
        return self.normalize(feature_vector)
    
    # Do vector search of audio
    def vector_search(self, embedding: np.ndarray) -> List[Dict[str, Any]]:
        print(embedding.tolist())
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",   
                    "path": "emb",
                    "queryVector": embedding.tolist(),
                    "numCandidates": 6,   
                    "limit": 1
                }
            },
            {
                "$project": {
                    "audio": 1,
                    "metadata": 1,
                    "score": { "$meta": "vectorSearchScore" },
                    "_id": 0
                }
            }
        ]
    
        try:
            results = list(self.sounds_collection.aggregate(pipeline))
            similarity_threshold = 0.99999
            filtered_results = [result for result in results if result.get("score", 0) >= similarity_threshold]

            if filtered_results:
                for result in filtered_results:
                    print("Audio:", result.get("audio", "No score found"))
                    print("Score:", result.get("score", "No score found"))
                return filtered_results
            else:
                print("No relevant matches found.")
                return []
        except Exception as e:
            return []


    def process_audio(self) -> None:
        audio = pyaudio.PyAudio()
        stream = None
        
        try:
            device_id = self.find_default_input_device()
            if device_id is None:
                raise ValueError("No input devices available")

            stream = audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.SAMPLE_RATE,
                input=True,
                frames_per_buffer=self.CHUNK_SIZE,
                input_device_index=device_id
            )
            logger.info(f"Audio stream opened successfully on device {device_id}")

            while self.running:
                frames = []
                stream.start_stream()
                

                for _ in range(int((self.SAMPLE_RATE / self.CHUNK_SIZE) * self.RECORD_SECONDS)):
                    if not self.running:
                        break
                    frame = stream.read(self.CHUNK_SIZE, exception_on_overflow=False)
                    frames.append(frame)

                if not self.running:
                    break

                stream.stop_stream()
                

                audio_data = np.frombuffer(b"".join(frames), dtype=np.int16)
                
                if len(audio_data) == 0:
                    logger.warning("Captured audio is empty!")
                    continue
                
                embedding = self.get_audio_embedding(audio_data)
                results = self.vector_search(embedding)

                if results:
                    self.results_collection.insert_one({
                        "sensor": self.sensor_name,
                        "data_time": datetime.now(),
                        "results": results
                    })
                    logger.info(f"Stored {len(results)} results")
                else:
                    logger.info("No matching results found")

        except Exception as e:
            logger.error(f"Error in audio processing: {e}")
        finally:
            if stream:
                stream.stop_stream()
                stream.close()
            audio.terminate()
            logger.info("Audio processing terminated")

    def start(self) -> None:
        logger.info("Starting audio processor...")
        self.running = True
        self.process_thread = threading.Thread(target=self.process_audio)
        self.process_thread.daemon = True
        self.process_thread.start()

    def stop(self) -> None:
        logger.info("Stopping audio processor...")
        self.running = False
        if hasattr(self, 'process_thread'):
            self.process_thread.join(timeout=5)
        self.client.close()
        logger.info("Audio processor stopped and cleaned up")

def main() -> None:
    
    processor = None
    try:
        processor = AudioProcessor(sensor_name="Audio Processor")
        processor.start()

        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("\nShutdown requested...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        if processor:
            processor.stop()

if __name__ == "__main__":
    main()