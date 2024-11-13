const express = require('express');
const app = express();
const http = require('http').createServer(app);
const io = require('socket.io')(http);
const { MongoClient } = require('mongodb');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
require('dotenv').config();

let clients = new Map();

app.use(express.json({ limit: '50mb' }));
app.use(express.static('public'));

const ProcessStatus = {
    STARTING: 'starting',
    RUNNING: 'running',
    ERROR: 'error',
    STOPPED: 'stopped'
};

class AudioProcessManager {
    constructor(socketId, io) {
        this.socketId = socketId;
        this.io = io;
        this.process = null;
        this.status = ProcessStatus.STOPPED;
        this.startTime = null;
    }

    getStatus() {
        return this.status;
    }

    async start() {
        if (this.process) {
            this.emitStatus('warning', 'Process already running');
            return false;
        }
        try {
            const scriptPath = path.join(__dirname, 'backend', 'audio_processor.py');
            this.process = spawn('python', [scriptPath], {
                env: { ...process.env, PYTHONUNBUFFERED: '1' }
            });
            this.startTime = Date.now();
            this.status = ProcessStatus.STARTING;
            this.setupProcessHandlers();
            return true;
        } catch (error) {
            this.handleError('Failed to start audio processor', error);
            return false;
        }
    }

    setupProcessHandlers() {
        this.process.stdout.on('data', (data) => {
            const output = data.toString().trim();
            console.log(`[AudioProcessor ${this.socketId}] ${output}`);
            if (output.includes('AudioProcessor initialized')) {
                this.status = ProcessStatus.RUNNING;
                this.emitStatus('running', 'Audio processor is now running');
            }
            if (output.includes('Captured')) {
                this.emitStatus('processing', output);
            }
        });

        this.process.stderr.on('data', (data) => {
            this.handleError('Audio processor error', data.toString().trim());
        });

        this.process.on('exit', (code, signal) => {
            const runtime = Date.now() - this.startTime;
            if (code === 0 && runtime < 1000) {
                this.handleError('Audio processor exited immediately', 'Check Python environment and dependencies');
            } else {
                this.emitStatus('stopped', `Audio processor ${signal ? 'killed' : 'exited'} ${signal || code}`);
            }
            this.cleanup();
        });
    }

    stop() {
        if (this.process) {
            this.status = ProcessStatus.STOPPED;
            this.process.kill();
            return true;
        }
        return false;
    }

    cleanup() {
        this.process = null;
        this.status = ProcessStatus.STOPPED;
        this.startTime = null;
    }

    handleError(message, error) {
        this.status = ProcessStatus.ERROR;
        console.error(`[AudioProcessor ${this.socketId}] ${message}:`, error);
        this.emitStatus('error', `${message}: ${error}`);
    }

    emitStatus(status, message) {
        this.io.to(this.socketId).emit('processingStatus', {
            status,
            message,
            timestamp: new Date().toISOString()
        });
    }
}

class MongoManager {
    constructor() {
        this.client = null;
        this.changeStream = null;
    }

    async connect() {
        try {
            console.log('Connecting to MongoDB...');
            this.client = new MongoClient(process.env.MONGO_CONNECTION_STRING);
            await this.client.connect();
            console.log('Connected to MongoDB successfully');
            this.setupChangeStream();
        } catch (error) {
            console.error('MongoDB connection error:', error);
            setTimeout(() => this.connect(), 5000);
        }
    }

    setupChangeStream() {
        const collection = this.client.db('audio').collection('results');
        this.changeStream = collection.watch([{ $match: { operationType: 'insert' } }]);
        this.changeStream.on('change', (change) => {
            console.log('New audio result detected');
            const result = change.fullDocument.results[0];
            io.emit('audioMatch', result);
        });

        this.changeStream.on('error', (error) => {
            console.error('Change stream error:', error);
            this.reconnect();
        });
    }

    async reconnect() {
        if (this.changeStream) {
            await this.changeStream.close();
            this.changeStream = null;
        }
        if (this.client) {
            await this.client.close();
            this.client = null;
        }
        setTimeout(() => this.connect(), 5000);
    }
}

const mongoManager = new MongoManager();
mongoManager.connect();

io.on('connection', (socket) => {
    console.log('Client connected:', socket.id);
    const manager = new AudioProcessManager(socket.id, io);
    clients.set(socket.id, manager);

    socket.on('startProcessing', async () => {
        console.log('Start processing requested by:', socket.id);
        await manager.start();
    });

    socket.on('stopProcessing', () => {
        console.log('Stop processing requested by:', socket.id);
        manager.stop();
    });

    socket.on('audioData', (data) => {
        // Validate incoming data
        if (!data || !data.audio || typeof data.audio !== 'string') {
            console.error('Invalid audio data received:', {
                hasData: !!data,
                hasAudio: !!(data && data.audio),
                audioType: data && data.audio ? typeof data.audio : 'undefined'
            });
            socket.emit('processingStatus', {
                status: 'error',
                message: 'Invalid audio data format received'
            });
            return;
        }
    
        try {
            console.log('Audio data received from client');
            
            const audioDir = path.join(__dirname, 'public');
            if (!fs.existsSync(audioDir)) {
                fs.mkdirSync(audioDir, { recursive: true });
            }
            
            const filePath = path.join(audioDir, `1.wav`);
            
            // Handle both full data URLs and raw base64
            let base64Data = data.audio;
            if (base64Data.includes('base64,')) {
                base64Data = data.audio.split('base64,')[1];
            }
    
            // Validate base64 string
            if (!base64Data || !/^[A-Za-z0-9+/=]+$/.test(base64Data)) {
                throw new Error('Invalid base64 audio data');
            }
    
            const audioBuffer = Buffer.from(base64Data, 'base64');
            
            fs.writeFile(filePath, audioBuffer, (err) => {
                if (err) {
                    console.error('Error saving audio file:', err);
                    socket.emit('processingStatus', {
                        status: 'error',
                        message: 'Failed to save audio recording: ' + err.message
                    });
                } else {
                    console.log(`Audio saved successfully: ${filePath}`);
                    socket.emit('recordingSaved', { 
                        status: 'success',
                        filePath,
                        message: 'Audio file saved successfully'
                    });
                }
            });
        } catch (error) {
            console.error('Error processing audio data:', error);
            socket.emit('processingStatus', {
                status: 'error',
                message: 'Error processing audio data: ' + error.message
            });
        }
    });

    socket.on('disconnect', () => {
        console.log('Client disconnected:', socket.id);
        const manager = clients.get(socket.id);
        if (manager) {
            manager.stop();
            clients.delete(socket.id);
        }
    });
});

app.get('/api/status', (req, res) => {
    res.json({
        server: 'running',
        clients: Array.from(clients.entries()).map(([id, manager]) => ({
            id,
            status: manager.getStatus()
        }))
    });
});

const PORT = process.env.PORT || 3000;
http.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});