import paho.mqtt.client as paho
from prometheus_client import Gauge, Enum, CollectorRegistry, push_to_gateway
from shapely.geometry import Point, Polygon
import json
import urllib.request
import urllib.parse
import time
import threading
import math
import matplotlib.pyplot as plt

def calculate_zone_detection(direction, zone, point):
    # Calculate orthogonal vector
    vecteur_orthogonal = {'x': -direction['y'], 'y': direction['x']}
    
    # Length and width of the zone
    l2 = zone["long"]
    l = zone["larg"]
    
    # Point coordinates
    x = point.x
    y = point.y
    
    # Calculate the norms
    norme_dir = math.sqrt(direction['x']**2 + direction['y']**2)
    norme_orthogonal = math.sqrt(vecteur_orthogonal['x']**2 + vecteur_orthogonal['y']**2)
    
    # Normalize the orthogonal vector
    vecteur_orthogonal['x'] /= norme_orthogonal
    vecteur_orthogonal['y'] /= norme_orthogonal
    
    # Normalize the direction vector
    direction['x'] /= norme_dir
    direction['y'] /= norme_dir
    
    # Calculate the points P1, P2, P3, P4
    P1 = (x + l2 * vecteur_orthogonal['x'] + l/2 * direction['x'], y + l2 * vecteur_orthogonal['y'] + l/2 * direction['y'])
    P2 = (x - l2 * vecteur_orthogonal['x'] + l/2 * direction['x'], y - l2 * vecteur_orthogonal['y'] + l/2 * direction['y'])
    P3 = (P1[0] + l * direction['x'] + l2/2 * vecteur_orthogonal['x'], P1[1] + l * direction['y'] + l2/2 * vecteur_orthogonal['y'])
    P4 = (P2[0] + l * direction['x'] - l2/2 * vecteur_orthogonal['x'], P2[1] + l * direction['y'] - l2/2 * vecteur_orthogonal['y'])

    P = (x, y)
    
    # Create and return the polygon
    final_zone = Polygon([P1, P, P2, P4, P3])
    return final_zone

import math

def calculate_direction(lat1, lon1, lat2, lon2):
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    distance = math.sqrt(dlat**2 + dlon**2)
    return {'x': dlon / distance, 'y': dlat / distance}

def predict_next_points(gps_data, num_predictions=3, time_step=5):
    timestamps = sorted(gps_data.keys())
    last_point = gps_data[timestamps[-1]]
    second_last_point = gps_data[timestamps[-2]]
    
    # Calculate the average direction
    direction = calculate_direction(second_last_point['latitude'], second_last_point['longitude'],
                                    last_point['latitude'], last_point['longitude'])
    
    # Calculate the average speed (in m/s)
    avg_speed = sum(point['vitesse'] for point in gps_data.values()) / len(gps_data) / 3.6  # km/h to m/s
    
    # Calculate distance traveled in time_step seconds
    step_distance = avg_speed * time_step  # Distance in meters

    predicted_points = {}
    current_point = last_point
    for i in range(1, num_predictions + 1):
        # Calculate the next point based on the direction and speed
        delta_lat = direction['y'] * step_distance / 111139  # Convert meters to degrees (approx. 111.139 km per degree)
        delta_lon = direction['x'] * step_distance / (111139 * math.cos(math.radians(current_point['latitude'])))
        
        next_lat = current_point['latitude'] + delta_lat
        next_lon = current_point['longitude'] + delta_lon
        
        # Estimate the date for the next point
        next_date = current_point['date'] + time_step
        
        predicted_points[timestamps[-1] + i] = {
            'date': next_date,
            'latitude': next_lat,
            'longitude': next_lon,
            'vitesse': avg_speed * 3.6,  # Convert back to km/h for consistency
            'distance': step_distance
        }
        
        # Update the current point
        current_point = {
            'date': next_date,
            'latitude': next_lat,
            'longitude': next_lon,
            'vitesse': avg_speed * 3.6,  # Convert back to km/h for consistency
            'distance': step_distance
        }
        
    return predicted_points

# Example usage

gps_data = {
    1721836574.277: {'date': 1721836567.3032665, 'latitude': 16.051108320558086, 'longitude': 108.22507352428653, 'vitesse': 1.5, 'distance': 105},
    1721836584.277: {'date': 1721836577.3032665, 'latitude': 16.051308320558086, 'longitude': 108.22517352428653, 'vitesse': 1.0, 'distance': 100},
    1721836594.277: {'date': 1721836587.3032665, 'latitude': 16.051608320558086, 'longitude': 108.22527352428653, 'vitesse': 1., 'distance': 5}
}



#if __name__ == '__main__':
    # point = Point(8, 5)
    # direction = {}
    # direction['x'] = 0.001
    # direction['y'] = 0.000
    
    # geojson_url = 'http://127.0.0.1:3030/data/zone-close-ship.json'
    # with urllib.request.urlopen(geojson_url) as url:
    #     data = json.loads(url.read().decode())
    #     zone = data
    #     print(zone)
    #     final_zone = calculate_zone_detection(direction, zone['pos'], point)
    #     # show on matplotlib
    #     import matplotlib.pyplot as plt
    #     # define landmark
    #     plt.plot(point.x, point.y, 'ro')
    #     # define axis landmark
    #     x,y = final_zone.exterior.xy
    #     plt.plot(x, y)
    #     plt.show()
    
predicted_points = predict_next_points(gps_data)

# Plotting the original and predicted trajectories
plt.figure(figsize=(10, 6))

# Original trajectory
latitudes = [gps_data[ts]['latitude'] for ts in sorted(gps_data.keys())]
longitudes = [gps_data[ts]['longitude'] for ts in sorted(gps_data.keys())]
plt.plot(longitudes, latitudes, 'go-', label='Original Trajectory')

# Predicted trajectory
pred_latitudes = [predicted_points[ts]['latitude'] for ts in sorted(predicted_points.keys())]
pred_longitudes = [predicted_points[ts]['longitude'] for ts in sorted(predicted_points.keys())]
plt.plot(pred_longitudes, pred_latitudes, 'ro-', label='Predicted Trajectory')

plt.xlabel('Longitude')
plt.ylabel('Latitude')
plt.title('Original and Predicted Trajectories')
plt.legend()
plt.grid(True)
plt.show()
