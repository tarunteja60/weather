from flask import Flask, render_template, request, redirect, send_file, url_for, session
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import pandas as pd

app = Flask(__name__)
app.secret_key = "1234"

# MongoDB setup
client = MongoClient('mongodb://localhost:27017/')
db = client['weather_forecaster']
users_collection = db['users']
weather_collection = db['weather']

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'username' in session:
        username = session['username']
        if request.method == 'POST':
            city_name = request.form.get('city')

            r = requests.get('https://api.openweathermap.org/data/2.5/weather?q='+city_name+'&appid=1c081163b6699f88a00572e53303aa01')
            json_object = r.json()

            # Check if the response contains valid weather data
            if 'main' in json_object:
                temperature = int(json_object['main']['temp']-273.15) 
                humidity = int(json_object['main']['humidity'])
                pressure = int(json_object['main']['pressure'])
                wind = int(json_object['wind']['speed'])

                condition = json_object['weather'][0]['main']
                desc = json_object['weather'][0]['description']

                # Save weather data to MongoDB
                weather_data = {
                    'username': username,
                    'city_name': city_name,
                    'temperature': temperature,
                    'humidity': humidity,
                    'pressure': pressure,
                    'wind_speed': wind,
                    'condition': condition,
                    'description': desc
                }
                weather_collection.insert_one(weather_data)

                return render_template('dashboard.html', username=username, temperature=temperature, pressure=pressure,
                                       humidity=humidity, city_name=city_name, condition=condition,
                                       wind=wind, desc=desc)
            else:
                error_message = "City not found. Please enter a valid city name."
                return render_template('dashboard.html', error_message=error_message)

        else:
            return render_template('dashboard.html')
    else:
        return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        existing_user = users_collection.find_one({'email': email})
        if existing_user:
            return "Email already exists!"
        
        username = request.form['username']
        password = request.form['password']

        hashed_password = generate_password_hash(password, method='sha256')

        user_data = {
            'email': email,
            'username': username,
            'password': hashed_password
        }

        users_collection.insert_one(user_data)

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = users_collection.find_one({'email': email})

        if user and check_password_hash(user['password'], password):
            session['username'] = user['username']
            return redirect(url_for('index'))

        return "Invalid email or password"
        
    return render_template('login.html')

@app.route('/export_to_excel', methods=['GET'])
def export_to_excel():
    if 'username' in session:
        cursor = weather_collection.find({'username': session['username']})
        df = pd.DataFrame(list(cursor))
        
        excel_file_path = 'weather_data.xlsx'
        df.to_excel(excel_file_path, index=False)
        
        return send_file(excel_file_path, as_attachment=True)
    else:
        return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
