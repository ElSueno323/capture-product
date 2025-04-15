from cv2.gapi import render
from flask import Flask, render_template, Response,request, jsonify, g
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
import threading

# Load environment variables


app = Flask(__name__)

# Initialize video capture


def findVideoSource():
    for i in range(3):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            print(f"Camera index {i} found")
            cap.release()
            return cv2.VideoCapture(i)
    else:
        print("No camera found")
        return None

cap = findVideoSource()   

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

def comparare_items(cart, predictions):
    if len(predictions) != len(cart):
        return False
    for item in predictions:
        if item['class'] not in cart:
            return False
    return True

def process_frame(frame):
    start_time = time.time()
    
    # Resize image to reduce size while maintaining aspect ratio
    height, width = frame.shape[:2]
    max_dimension = 1080
    scale = max_dimension / max(height, width)
    if scale < 1:
        new_width = int(width * scale)
        new_height = int(height * scale)
        frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
    
    # Save frame temporarily for local 
    temp_path = 'temp_frame.jpg'
    if os.path.exists(temp_path):
        os.remove(temp_path)
    cv2.imwrite(temp_path, frame)
    
    # Convert frame to base64 for API
    _, img_encoded = cv2.imencode('.jpg', frame)
    img_base64 = base64.b64encode(img_encoded).decode('utf-8')
    
    preprocessing_time = time.time() - start_time
    
    try:
        # Variables pour stocker les résultats des threads
        api_predictions = None
        local_time = 0
        api_time = 0

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
        #local_thread = threading.Thread(target=local_inference)
        api_thread = threading.Thread(target=api_inference)
        
        #local_thread.start()
        api_thread.start()
        
        # Attendre que les deux threads se terminent
        #local_thread.join()
        api_thread.join()
        
        # Create a copy of frame for drawing
        frame_with_predictions = frame.copy()
        
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
            'api_inference_time': api_time,
            'total_time': total_time,
            'time_difference': abs(local_time - api_time)
        }
        
        return frame_with_predictions, {
            'api_predictions': api_predictions,
            'timing': timing_info
        }
    
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return frame, {"error": str(e)}

def load_items():
    with open("data/items.json", "r", encoding="utf-8") as file:
        return json.load(file)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/menu')
def menu():
    return render_template('menu.html' )

@app.route('/items')
def items():
    items = load_items()  
    return items

@app.route('/compare', methods=['POST'])
def compare():
    cart = request.get_json()
    success = False
    
    init_time = time.time()
    for i in range(7):
        start_time = time.time()
        success, frame = cap.read()
        capture_time = time.time() - start_time
        print(f"Tentative {i+1}: Temps de capture = {capture_time:.3f} secondes | Succès: {success}")
    print(f"Temps total de capture = {time.time() - init_time:.3f} secondes")
    
    if success:
        processed_frame, predictions = process_frame(frame)
        
        # Convert processed frame to base64 for sending to frontend
        _, buffer = cv2.imencode('.jpg', processed_frame)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        img_data = f'data:image/jpeg;base64,{img_base64}'
        
        # Extraire les prédictions de l'API
        api_predictions = predictions.get('api_predictions', {})
        predictions_array = api_predictions.get('predictions', [])

        # Comparer les éléments du panier avec les prédictions
        equal = all(any(item == pred['class'] for pred in predictions_array) for item in cart)

        equal = comparare_items(cart, predictions_array)

        print("Predictions from API:", predictions_array)
        return render_template('compare.html', predictions=predictions_array, cart=cart, equal=equal, image=img_data)
    
    return jsonify({'status': 'error', 'message': 'Failed to capture image'})

@app.route('/fast_compare')
def test():
    image_path = 'test_item.jpg'
    frame = cv2.imread(image_path)
    memory_size = frame.nbytes
    proced_frame,predilection = process_frame(frame)
    image_size=os.path.getsize(image_path)
    size_image= {
        "kb":image_size/1024,
        "mb":image_size/1024/1024,
        "memory_size": memory_size,
        }
    return jsonify({'predictions':predilection},{'size_image':size_image})

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

@app.before_request
def start_timer():
    g.start_time = time.time()
    g.request_size = int(request.content_length or 0)

@app.after_request
def log_bandwidth_usage(response):
    duration = time.time() - g.start_time
    response_size = response.calculate_content_length()
    total = (g.request_size or 0) + (response_size or 0)
    print(f"[BANDWIDTH] {request.method} {request.path} | Requête: {g.request_size} B | Réponse: {response_size} B | Total: {total / 1024:.2f} KB | Temps: {duration:.2f}s")
    return response

if __name__ == '__main__':
    load_dotenv()

    app.run(debug=False, port=int(os.getenv('PORT',5002)))
