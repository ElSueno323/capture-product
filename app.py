from flask import Flask, render_template, Response, jsonify
import cv2
import base64
import requests
import json
import time
from io import BytesIO
from PIL import Image
from roboflow import Roboflow
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize video capture
cap = cv2.VideoCapture(0)

# Initialize Roboflow model
rf = Roboflow(api_key=os.getenv('ROBOFLOW_API_KEY'))
project = rf.workspace().project(os.getenv('ROBOFLOW_PROJECT'))
model = project.version(int(os.getenv('ROBOFLOW_VERSION'))).model

def generate_frames():
    while True:
        success, frame = cap.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

import threading

def process_frame(frame):
    start_time = time.time()
    
    # Resize image to reduce size while maintaining aspect ratio
    height, width = frame.shape[:2]
    max_dimension = 800
    scale = max_dimension / max(height, width)
    if scale < 1:
        new_width = int(width * scale)
        new_height = int(height * scale)
        frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
    
    # Save frame temporarily for local inference
    temp_path = 'temp_frame.jpg'
    cv2.imwrite(temp_path, frame)
    
    # Convert frame to base64 for API
    _, img_encoded = cv2.imencode('.jpg', frame)
    img_base64 = base64.b64encode(img_encoded).decode('utf-8')
    
    preprocessing_time = time.time() - start_time
    
    try:
        # Variables pour stocker les résultats des threads
        local_predictions = None
        api_predictions = None
        local_time = 0
        api_time = 0
        
        # Fonction pour l'inférence locale
        def local_inference():
            nonlocal local_predictions, local_time
            local_start = time.time()
            local_predictions = model.predict(temp_path, confidence=40, overlap=30).json()
            local_time = time.time() - local_start
        
        # Fonction pour l'inférence API
        def api_inference():
            nonlocal api_predictions, api_time
            api_start = time.time()
            response = requests.post(
                f"{os.getenv('ROBOFLOW_API_URL')}/{os.getenv('ROBOFLOW_PROJECT')}/{os.getenv('ROBOFLOW_VERSION')}",
                data=img_base64,
                params={"api_key": os.getenv('ROBOFLOW_API_KEY')},
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            api_predictions = response.json()
            api_time = time.time() - api_start
        
        # Créer et démarrer les threads
        local_thread = threading.Thread(target=local_inference)
        api_thread = threading.Thread(target=api_inference)
        
        local_thread.start()
        api_thread.start()
        
        # Attendre que les deux threads se terminent
        local_thread.join()
        api_thread.join()
        
        # Create a copy of frame for drawing
        frame_with_predictions = frame.copy()
        
        # Draw local predictions in orange
        for pred in local_predictions.get('predictions', []):
            x = int(pred['x'] - pred['width']/2)
            y = int(pred['y'] - pred['height']/2)
            w = int(pred['width'])
            h = int(pred['height'])
            cv2.rectangle(frame_with_predictions, (x, y), (x + w, y + h), (0, 165, 255), 2)
            label = f"{pred['class']}: {pred['confidence']:.0%}"
            cv2.putText(frame_with_predictions, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 165, 255), 2)
        
        # Draw API predictions in green
        for pred in api_predictions.get('predictions', []):
            x = int(pred['x'] - pred['width']/2)
            y = int(pred['y'] - pred['height']/2)
            w = int(pred['width'])
            h = int(pred['height'])
            cv2.rectangle(frame_with_predictions, (x, y), (x + w, y + h), (0, 255, 0), 2)
            label = f"{pred['class']}: {pred['confidence']:.0%}"
            cv2.putText(frame_with_predictions, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        
        total_time = time.time() - start_time
        
        timing_info = {
            'preprocessing_time': preprocessing_time,
            'local_inference_time': local_time,
            'api_inference_time': api_time,
            'total_time': total_time,
            'time_difference': abs(local_time - api_time)
        }
        
        return frame_with_predictions, {
            'local_predictions': local_predictions,
            'api_predictions': api_predictions,
            'timing': timing_info
        }
    
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return frame, {"error": str(e)}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/capture', methods=['POST'])
def capture():
    success, frame = cap.read()
    if success:
        processed_frame, predictions = process_frame(frame)
        
        # Convert processed frame to base64 for sending to frontend
        _, buffer = cv2.imencode('.jpg', processed_frame)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return jsonify({
            'status': 'success',
            'image': img_base64,
            'predictions': predictions
        })
    
    return jsonify({'status': 'error', 'message': 'Failed to capture image'})

if __name__ == '__main__':
    app.run(debug=True)