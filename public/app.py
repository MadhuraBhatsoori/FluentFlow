from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from functools import lru_cache
import os
from dotenv import load_dotenv
import logging
from datetime import datetime
import time

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app) 

GOOGLE_API_KEY='AIzaSyCiVBKK51Rf4VO82AaFiXRNfCCEFGlTcDU'
genai.configure(api_key='AIzaSyCiVBKK51Rf4VO82AaFiXRNfCCEFGlTcDU')

myfile = genai.upload_file("1.wav")
print(f"{myfile=}")


# Configure Gemini AI
try:
    genai.configure(api_key='AIzaSyCiVBKK51Rf4VO82AaFiXRNfCCEFGlTcDU')
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    logger.error(f"Failed to configure Gemini AI: {str(e)}")
    raise



# Analysis prompts with more detailed instructions
ANALYSIS_PROMPTS = {
    'sentenceStructure': """
    Analyze the following aspects of the speech:
    1. Grammar accuracy and consistency
    2. Sentence complexity and variety
    3. Use of transitions and connectors
    4. Proper word order and structure
    
    Provide a concise analysis result in the format of Analysis: give analysis in 3 sentences 
    Then in next line, 
    Provide suggestion on how to improve in the format of Suggestions: Give suggestions in 3 sentences
    """,
    
    'speechClarity': """
    Evaluate the following aspects of speech delivery:
    1. Pronunciation clarity
    2. Speaking pace and rhythm
    3. Voice projection
    4. Articulation of words
    
    Provide a concise analysis result in the format of Analysis: give analysis in 3 sentences 
    Then in next line, 
    Provide suggestion on how to improve in the format of Suggestions: Give suggestions in 3 sentences
    """,
    
    'confidencePitch': """
    Assess the following aspects of the speaker's delivery:
    1. Confidence level in voice
    2. Pitch variation and expression
    3. Vocal tone and emotion
    4. Speaking authority
    
    Provide a concise analysis result in the format of Analysis: give analysis in 3 sentences 
    Then in next line, 
    Provide suggestion on how to improve in the format of Suggestions: Give suggestions in 3 sentences
    """
}


class AnalysisCache:
    def __init__(self, max_size=100):
        self.cache = {}
        self.max_size = max_size
        
    def get(self, key):
        if key in self.cache:
            value, timestamp = self.cache[key]
            # Cache entries expire after 1 hour
            if time.time() - timestamp < 3600:
                return value
            else:
                del self.cache[key]
        return None
        
    def set(self, key, value):
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            oldest = min(self.cache.items(), key=lambda x: x[1][1])
            del self.cache[oldest[0]]
        self.cache[key] = (value, time.time())

# Initialize cache
analysis_cache = AnalysisCache()

@app.route('/api/analyze', methods=['POST'])
def analyze_speech():
    try:
        start_time = time.time()
        logger.info("Received analysis request")
        
        data = request.get_json()
        
        # Generate cache key based on request data
        cache_key = str(hash(str(data)))
        
        # Check cache
        cached_result = analysis_cache.get(cache_key)
        if cached_result:
            logger.info("Returning cached result")
            return jsonify({
                'success': True,
                'results': cached_result,
                'cached': True
            })

        # Simulate audio processing delay (remove in production)
        time.sleep(1)
        
        # Process each analysis aspect
        results = {}
        for aspect, prompt in ANALYSIS_PROMPTS.items():
            try:
                #response = model.generate_content(prompt)
                response = model.generate_content([myfile, prompt])
                
            
                # Process the response based on aspect
                if aspect == 'sentenceStructure':
                    analysis = response.text
                elif aspect == 'speechClarity':
                    analysis = response.text
                elif aspect == 'confidencePitch':
                    analysis = response.text
                else:
                    analysis = response.text
                
                results[aspect] = analysis
                
            except Exception as e:
                logger.error(f"Error generating {aspect} analysis: {str(e)}")
                results[aspect] = f"Analysis unavailable: {str(e)}"

        # Cache the results
        analysis_cache.set(cache_key, results)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        logger.info(f"Analysis completed in {processing_time:.2f} seconds")
        
        return jsonify({
            'success': True,
            'results': results,
            'processingTime': processing_time
        })

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })

def initialize_app():
    """Initialize the application with required setup"""
    try:
        
        # Additional setup can be added here
        logger.info("Application initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        raise

if __name__ == '__main__':
    try:
        initialize_app()
        port = int(os.getenv('PORT', 5000))
        debug = os.getenv('FLASK_ENV') == 'development'
        
        app.run(host='0.0.0.0', port=port, debug=debug)
        
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        raise