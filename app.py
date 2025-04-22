from flask import Flask, render_template, request, jsonify
from geopy.geocoders import Nominatim
import json
import os

app = Flask(__name__)

with open('data/pet_care.json', 'r', encoding='utf-8') as f:
    pet_care_data = json.load(f)

def get_nearby_shelters(location):
    return [
        {"name": "Happy Paws Shelter", "address": "123 Pet Street, " + location, "distance": "2.5 miles"},
        {"name": "Furry Friends Rescue", "address": "456 Animal Avenue, " + location, "distance": "3.1 miles"},
        {"name": "Paws and Claws Sanctuary", "address": "789 Rescue Road, " + location, "distance": "4.2 miles"}
    ]

def get_pet_care_info(topic):
    return pet_care_data.get(topic, "I'm sorry, I don't have information about that topic yet.")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '').lower()
    
    if 'shelter' in message or 'adopt' in message:
        location = data.get('location', '')
        shelters = get_nearby_shelters(location)
        return jsonify({
            'response': 'Here are some nearby shelters:',
            'shelters': shelters
        })
    
    elif 'care' in message or 'feed' in message or 'vaccine' in message:
        topic = 'general_care'  # Default topic
        if 'feed' in message:
            topic = 'feeding'
        elif 'vaccine' in message:
            topic = 'vaccination'
        elif 'adapt' in message or 'new home' in message:
            topic = 'adaptation'
        
        info = get_pet_care_info(topic)
        return jsonify({
            'response': info
        })
    
    else:
        return jsonify({
            'response': "I can help you with information about pet adoption, nearby shelters, and pet care. What would you like to know?"
        })

if __name__ == '__main__':
    app.run(debug=True) 