from flask import Flask, request, render_template, jsonify
from route_optimizer import RouteOptimizer

app = Flask(__name__)

# Initialize RouteOptimizer with the dataset
optimizer = RouteOptimizer(csv_file="TG_ev_charging_stations.csv")

@app.route('/')
def Home():
    return render_template('Route_Optimization.html')

@app.route('/optimize_route', methods=['POST'])
def optimize_route():
    if not optimizer.charging_stations:
        return jsonify({"error": "Charging station data not loaded."}), 400

    data = request.json
    try:
        result = optimizer.optimize_route(
            start_name=data["start_location"],
            destination_name=data["destination_location"],
            range_km=data["range"]
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)


