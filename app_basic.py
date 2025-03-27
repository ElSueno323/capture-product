from flask import Flask, render_template, Response, jsonify
import cv2
import base64
import requests
import json
import time
from io import BytesIO
from PIL import Image

app = Flask(__name__)

# Initialize video capture
cap = cv2.VideoCapture(0)
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

def process_frame(frame):
    # Resize image to reduce size while maintaining aspect ratio
    height, width = frame.shape[:2]
    max_dimension = 800
    scale = max_dimension / max(height, width)
    if scale < 1:
        new_width = int(width * scale)
        new_height = int(height * scale)
        frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
    
    # Convert frame to JPEG format with compression
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, 80]
    _, img_encoded = cv2.imencode('.jpg', frame, encode_params)
    # Convert to base64
    img_base64 = base64.b64encode(img_encoded).decode('utf-8')
    
    # Roboflow API configuration
    api_url = "https://detect.roboflow.com/caisse-verfication/3"
    api_key = "Oj8rbnsYxkC2M303mMMJ"
    
    try:
        # Send request to Roboflow API
        response = requests.post(
            api_url,
            data=img_base64,
            params={"api_key": api_key},
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        
        predictions = response.json()
        
        # Draw rectangles and labels on the frame
        for pred in predictions.get('predictions', []):
            x = int(pred['x'] - pred['width']/2)
            y = int(pred['y'] - pred['height']/2)
            w = int(pred['width'])
            h = int(pred['height'])
            
            # Draw rectangle
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # Add label
            class_name = pred['class']
            confidence = pred['confidence']
            label = f"{class_name}: {confidence:.0%}"
            cv2.putText(frame, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255,255,255), 2)
        
        return frame, predictions
    
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