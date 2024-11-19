# FluentFlow

## Testing Instructions

1. Clone the repository
2. Install dependencies:
   pip install pyaudio
   pip install numpy
   pip install pymongo
   pip install librosa
   pip install panns_inference
   pip install torch
   pip install python-dotenv
   pip install certifi
3. Run app.js
4. Go to public folder:
   Run  

## Inspiration

In today's competitive world, effective communication is one of the most crucial skills for leadership and career growth. Yet many women face barriers in expressing their ideas confidently, clearly, and with the structure needed to influence decision-making and leadership dynamics. To address this, we built an AI-powered real-time speech analysis tool that provides actionable insights to improve clarity, structure, and confidence in communication. This tool empowers users by giving detailed feedback, helping them grow their leadership presence and career potential. By delivering personalised, data-driven guidance, tool aims provide support to overcome communication challenges and thrive in leadership roles.

## What it does

The tool provides users with the ability to refine their communication skills through a dynamic, interactive experience. Here's how it works:

Start Recording: The user begins by recording their speech on any topic. This can be for a presentation, a meeting rehearsal, or simply practicing everyday conversations.

Instant Feedback on Filler Words: While speaking, the tool monitors for the use of filler words (such as "um," "uh," "like," and "you know"). Whenever filler words are detected repeatedly, the speaker icon changes from green to red, giving an immediate visual cue that the user is relying on fillers too often. This allows them to adjust their speech in real time, fostering greater awareness and control over their communication habits.

Recording Completed: Once the user finishes speaking, the full speech recording is sent to Gemini for an in-depth analysis of several key aspects:

Sentence Structure and Grammar: Evaluates the flow and coherence of sentences, highlighting any grammatical errors or areas where clarity can be improved.

Speech Clarity and Pace: Assesses how clearly the user enunciates words and the pacing of their speech, offering feedback on whether they’re speaking too quickly or too slowly.

Pitch and Confidence: Analyzes vocal tone and pitch variation, providing insights into the confidence level of the speaker based on vocal patterns.

Feedback: The user receives a score out of 100, along with a detailed analysis of their performance.

## How we built it

Frontend (HTML and CSS): The user interface is built with HTML and CSS, designed to be simple and responsive. The main elements include a Start Recording button, a Speaker Icon (which changes color based on filler word detection). The frontend captures audio from the user’s microphone and sends it to the backend in real-time.

Backend (Node.js Server): Node.js manages the incoming audio data from the frontend and facilitates communication between the different services. When the user starts recording, audio data is processed and broken down into small segments that can be analysed for filler words. Real-time Analysis: As the audio segments are received, they are checked against a database of filler word embeddings (stored in MongoDB Atlas). Each incoming audio segment is converted into a vector (embedding) and matched in real-time through a vector search. If filler words are detected frequently, the server sends a signal to the frontend to change the speaker icon from green to red.

MongoDB Atlas (Database): MongoDB Atlas is used to store embeddings of common filler words. This allows for fast vector-based searches, helping to identify when the user is using filler words in real-time. Each filler word audio segment is preprocessed and stored as a vector in the database for efficient retrieval and matching.

Gemini Analysis (Flask API): After the user completes their recording, the full audio is sent to Gemini, which is connected through a Flask API. Gemini performs a deeper analysis on: Sentence Structure and Grammar: It evaluates sentence flow and highlights grammar issues. Speech Clarity and Pace: It assesses pronunciation clarity and speed. Pitch and Confidence: It analyzes vocal pitch and tone variation to estimate the confidence level of the speaker. Once Gemini completes the analysis, it returns a score and detailed feedback.

Feedback and Scoring: The feedback, including the score (out of 100) and specific areas of improvement, is then displayed on the frontend for the user.This breakdown includes detailed insights and suggestions on sentence structure, grammar, speech pace, clarity, pitch, and overall confidence, helping the user refine their communication skills effectively.

## Future Scope

The future scope of this speech analysis tool is vast, with potential to enhance its capabilities and broaden its impact. Future developments could include multilingual support, emotion and sentiment analysis, and adaptive learning for more personalised feedback. The tool could integrate with professional development programs and video conferencing platforms, providing real-time feedback during meetings and presentations. Expanding its audience beyond women to include professionals, students, and public speakers, as well as career-specific coaching, would further its reach. Additionally, with gamification and voice inclusivity would make speech improvement more engaging and accessible to all. These advancements would drive greater gender equality, professional growth, and communication effectiveness.
