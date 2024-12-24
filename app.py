from flask import Flask, url_for, render_template, request, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
import pickle
import os
import logging
from route_optimizer import RouteOptimizer 
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'secret_key'

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    city = db.Column(db.String(120), nullable=False)
    country = db.Column(db.String(120), nullable=False)

class EV(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    ev_name = db.Column(db.String(120), nullable=False)
    ev_model = db.Column(db.String(120), nullable=False)
    licensePlate = db.Column(db.String(120), unique=True, nullable=False)
    year = db.Column(db.Integer, nullable=False)

class DriverBehavior(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.String(50), nullable=False)
    trip_id = db.Column(db.String(50), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)  
    timestamp = db.Column(db.DateTime, nullable=False)
    value = db.Column(db.Float, nullable=False)  

class MaintenanceAlert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.String(50), nullable=False)
    issue = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(20), nullable=False) 
    timestamp = db.Column(db.DateTime, nullable=False)

with open('Model.pkl', 'rb') as model_file:
    model = pickle.load(model_file)

route_optimizer = RouteOptimizer()

@app.route('/', methods=['GET'])
def Home():
    if session.get('logged_in'):
        return render_template('Home.html')
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            session['logged_in'] = True
            session['email'] = email
            return redirect(url_for('Home'))
        else:
            return render_template('login.html', error="Invalid email or password")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        city = request.form.get('city')
        country = request.form.get('country')

        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            return render_template('register.html', error="Username or email already exists")

        new_user = User(username=username, password=password, email=email, city=city, country=country)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/EV_Registration', methods=['GET', 'POST'])
def EV_Registration():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        owner_name = request.form.get('owner_name')
        ev_name = request.form.get('ev_name')
        ev_model = request.form.get('ev_model')
        licensePlate = request.form.get('licensePlate')
        year = request.form.get('year')
        phone = request.form.get('phone')

        if EV.query.filter_by(licensePlate=licensePlate).first():
            return render_template('EV_Registration.html', error="License Plate number already exists.")

        new_ev = EV(
            owner_name=owner_name,
            phone=phone,
            ev_name=ev_name,
            ev_model=ev_model,
            licensePlate=licensePlate,
            year=int(year)
        )
        db.session.add(new_ev)
        db.session.commit()
        return redirect(url_for('Home'))
    return render_template('EV_Registration.html')

@app.route('/Vehicle_status')
def Vehicle_status():
    return render_template('Vehicle_status.html')

@app.route('/Battery_status', methods=['GET', 'POST'])
def Battery_status():
    if request.method == 'POST':
        try:
            # Get form data
            voltage = float(request.form['Voltage'])
            temperature = float(request.form['Temperature'])
            internal_resistance = float(request.form['Internal_resistance'])

            # Prepare input data
            input_data = pd.DataFrame([{
                "Voltage": voltage,
                "Temperature": temperature,
                "Internal_resistance": internal_resistance
            }])

            # Predict battery health
            prediction = model.predict(input_data)[0]

            # Render the result
            return render_template('Battery_status.html',
                                   prediction_text=f'Predicted Battery Health: {round(prediction, 2)}%')
        except Exception as e:
            return render_template('Battery_status.html',
                                   error_text=f"Error: {str(e)}")
    return render_template('Battery_status.html')

@app.route('/Route_Optimization', methods=['GET', 'POST'])
def Route_Optimization():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            data = request.form if request.content_type != 'application/json' else request.json

            battery_level = int(data.get('battery_level', 0))
            start_location = data.get('start_location')
            destination_location = data.get('destination_location')
            ev_range = int(data.get('range', 0))

            results = route_optimizer.optimize_route(
                start_name=start_location,
                destination_name=destination_location,
                range_km=ev_range
            )

            if results:
                return render_template(
                    'Route_results.html',
                    fastest_route_url=results["fastest_route_url"],
                    stations_in_range=results["stations_in_range"]
                )
            else:
                return jsonify({"error": "No suitable charging stations found."}), 400
        except Exception as e:
            logging.error(f"Route optimization failed: {e}")
            return jsonify({"error": "An error occurred while optimizing the route."}), 500

    return render_template('Route_Optimization.html')

@app.route('/driver_behaviour')
def driver_behaviour():
    drivers = [
        {"driver_name": "John Doe", "speeding": 2, "harsh_braking": 1, "harsh_acceleration": 1, "sharp_turns": 1, "idle_time": 5, "distance_driven": 120, "fuel_consumption": 6, "acceleration_time": 5.4, "behavior_score": 15},
        {"driver_name": "Jane Smith", "speeding": 1, "harsh_braking": 0, "harsh_acceleration": 0, "sharp_turns": 0, "idle_time": 3, "distance_driven": 80, "fuel_consumption": 5, "acceleration_time": 4.8, "behavior_score": 10},
        {"driver_name": "Tom Harris", "speeding": 3, "harsh_braking": 2, "harsh_acceleration": 1, "sharp_turns": 2, "idle_time": 8, "distance_driven": 140, "fuel_consumption": 7, "acceleration_time": 6.2, "behavior_score": 18},
        {"driver_name": "Alice Johnson", "speeding": 0, "harsh_braking": 1, "harsh_acceleration": 0, "sharp_turns": 1, "idle_time": 6, "distance_driven": 110, "fuel_consumption": 6, "acceleration_time": 5.1, "behavior_score": 12},
        {"driver_name": "Michael Lee", "speeding": 2, "harsh_braking": 3, "harsh_acceleration": 2, "sharp_turns": 3, "idle_time": 9, "distance_driven": 160, "fuel_consumption": 8, "acceleration_time": 6.0, "behavior_score": 20},
        {"driver_name": "Sara Miller", "speeding": 1, "harsh_braking": 0, "harsh_acceleration": 0, "sharp_turns": 1, "idle_time": 4, "distance_driven": 95, "fuel_consumption": 5, "acceleration_time": 4.7, "behavior_score": 11},
        {"driver_name": "David Clark", "speeding": 4, "harsh_braking": 2, "harsh_acceleration": 1, "sharp_turns": 2, "idle_time": 7, "distance_driven": 180, "fuel_consumption": 9, "acceleration_time": 5.8, "behavior_score": 19},
        {"driver_name": "Sophia Scott", "speeding": 1, "harsh_braking": 1, "harsh_acceleration": 0, "sharp_turns": 0, "idle_time": 5, "distance_driven": 120, "fuel_consumption": 6, "acceleration_time": 5.2, "behavior_score": 14},
        {"driver_name": "James White", "speeding": 2, "harsh_braking": 1, "harsh_acceleration": 1, "sharp_turns": 1, "idle_time": 6, "distance_driven": 130, "fuel_consumption": 7, "acceleration_time": 5.9, "behavior_score": 16},
        {"driver_name": "Emily Brown", "speeding": 1, "harsh_braking": 1, "harsh_acceleration": 1, "sharp_turns": 1, "idle_time": 5, "distance_driven": 100, "fuel_consumption": 6, "acceleration_time": 5.3, "behavior_score": 13}
    ]
    
    # Render the template with the drivers data
    return render_template('Driver_behaviour.html', drivers=drivers)

@app.route('/maintenance_alerts', methods=['GET'])
def maintenance_alerts():
    return render_template('maintenance_alerts.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('Cost and Energy Consumption.html')

# Dash App Initialization
dash_app = dash.Dash(
    __name__,
    server=app,
    url_base_pathname='/dashboard/',
)

data = pd.read_csv('ev_fleet_dataset.csv')
if 'Year' not in data.columns:
    data['Year'] = 2023

dash_app.layout = html.Div([
    html.H1("EV Fleet Dashboard", style={'textAlign': 'center', 'margin-bottom': '20px'}),

    html.Div([
        html.Div([
            html.Label("Select Vehicle ID:"),
            dcc.Dropdown(
                id='vehicle-filter',
                options=[{'label': vehicle, 'value': vehicle} for vehicle in sorted(data['Vehicle_ID'].unique())],
                value=data['Vehicle_ID'].iloc[0],
                clearable=False
            )
        ], style={'flex': '1', 'margin-right': '10px'}),

        html.Div([
            html.Label("Select Route Type:"),
            dcc.Dropdown(
                id='route-filter',
                options=[{'label': route, 'value': route} for route in data['Route_Type'].unique()] + [{'label': 'All', 'value': 'All'}],
                value='All',
                clearable=False
            )
        ], style={'flex': '1', 'margin-right': '10px'}),

        html.Div([
            html.Label("Select Year:"),
            dcc.Dropdown(
                id='year-filter',
                options=[{'label': year, 'value': year} for year in sorted(data['Year'].unique())] + [{'label': 'All', 'value': 'All'}],
                value='All',
                clearable=False
            )
        ], style={'flex': '1'})
    ], style={'display': 'flex', 'margin-bottom': '20px'}),

    html.Div([
        html.Div(id='total-distance', style={
            'background': '#f9f9f9', 'padding': '20px', 'border-radius': '5px', 'textAlign': 'center', 'flex': '1', 'box-shadow': '0 2px 5px rgba(0, 0, 0, 0.1)'}),
        html.Div(id='average-efficiency', style={
            'background': '#f9f9f9', 'padding': '20px', 'border-radius': '5px', 'textAlign': 'center', 'flex': '1', 'box-shadow': '0 2px 5px rgba(0, 0, 0, 0.1)'}),
        html.Div(id='total-cost', style={
            'background': '#f9f9f9', 'padding': '20px', 'border-radius': '5px', 'textAlign': 'center', 'flex': '1', 'box-shadow': '0 2px 5px rgba(0, 0, 0, 0.1)'}),
    ], style={'display': 'flex', 'gap': '20px', 'margin-bottom': '20px'}),

    html.Div([
        html.H3("Energy Consumption Over Time", style={'textAlign': 'center', 'margin-bottom': '10px'}),
        dcc.Graph(id='energy-consumption-graph')
    ], style={'margin-bottom': '20px'}),

    html.Div([
        html.H3("Operational Cost Over Time", style={'textAlign': 'center', 'margin-bottom': '10px'}),
        dcc.Graph(id='operational-cost-graph')
    ])
])

@dash_app.callback([
    Output('total-distance', 'children'),
    Output('average-efficiency', 'children'),
    Output('total-cost', 'children'),
    Output('energy-consumption-graph', 'figure'),
    Output('operational-cost-graph', 'figure')
], [
    Input('vehicle-filter', 'value'),
    Input('route-filter', 'value'),
    Input('year-filter', 'value')
])
def update_dashboard(selected_vehicle, selected_route, selected_year):
    filtered_data = data[data['Vehicle_ID'] == selected_vehicle]
    if selected_route != 'All':
        filtered_data = filtered_data[filtered_data['Route_Type'] == selected_route]
    if selected_year != 'All':
        filtered_data = filtered_data[filtered_data['Year'] == selected_year]

    total_distance = filtered_data['Distance_Travelled_km'].sum()
    average_efficiency = filtered_data['Efficiency_kWh_per_km'].mean()
    total_cost = filtered_data['Operational_Cost_USD'].sum()

    energy_consumption_fig = px.line(
        filtered_data, x='Year', y='Energy_Consumption_kWh',
        title=f'Energy Consumption for Vehicle {selected_vehicle}',
        labels={'Energy_Consumption_kWh': 'Energy Consumption (kWh)', 'Year': 'Year'},
        markers=True
    )

    operational_cost_fig = px.line(
        filtered_data, x='Year', y='Operational_Cost_USD',
        title=f'Operational Cost for Vehicle {selected_vehicle}',
        labels={'Operational_Cost_USD': 'Operational Cost (USD)', 'Year': 'Year'},
    )


    return (
        f"Total Distance: {total_distance:.2f} km",
        f"Average Efficiency: {average_efficiency:.2f} kWh/km",
        f"Total Cost: ${total_cost:.2f}",
        energy_consumption_fig,
        operational_cost_fig
    )




@app.route('/Logout')
def Logout():
    session.pop('logged_in', None)
    session.pop('email', None)
    return redirect(url_for('login'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  
    app.run(debug=True)