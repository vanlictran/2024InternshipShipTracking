import math
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import CubicSpline
from shapely.geometry import Polygon

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0  # Rayon de la Terre en km
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c

def move_point(lat, lon, distance, bearing):
    R = 6371.0  # Rayon de la Terre en km
    lat = np.radians(lat)
    lon = np.radians(lon)
    lat2 = np.arcsin(np.sin(lat) * np.cos(distance / R) + np.cos(lat) * np.sin(distance / R) * np.cos(bearing))
    lon2 = lon + np.arctan2(np.sin(bearing) * np.sin(distance / R) * np.cos(lat), np.cos(distance / R) - np.sin(lat) * np.sin(lat2))
    return np.degrees(lat2), np.degrees(lon2)

def calculate_perpendicular(lat1, lon1, lat2, lon2, number_point, scale_km=0.1):
    distance = haversine_distance(lat1, lon1, lat2, lon2)
    bearing = math.atan2(lon2 - lon1, lat2 - lat1)

    # Calculer le vecteur perpendiculaire (en radians)
    perp_bearing1 = bearing + math.pi / 2
    perp_bearing2 = bearing - math.pi / 2

    # Calculer les points de la perpendiculaire
    perp_point1 = move_point(lat2, lon2, number_point * scale_km, perp_bearing1)
    perp_point2 = move_point(lat2, lon2, number_point * scale_km, perp_bearing2)

    return perp_point1, perp_point2

def predict_next_points(gps_data, num_predictions=3, time_step=20, base_error_step=0.2):
    timestamps = sorted(gps_data.keys())
    last_point = gps_data[timestamps[-1]]
    
    # Extract latitudes, longitudes, times, and speeds
    latitudes = [gps_data[ts]['latitude'] for ts in timestamps]
    longitudes = [gps_data[ts]['longitude'] for ts in timestamps]
    times = [gps_data[ts]['date'] for ts in timestamps]
    speeds = [gps_data[ts]['vitesse'] for ts in timestamps]
    
    # Create a cubic spline interpolation of latitude and longitude over time
    cs_lat = CubicSpline(times, latitudes)
    cs_lon = CubicSpline(times, longitudes)
    
    predicted_points = {}
    last_time = times[-1]
    current_time = last_time
    
    for i in range(1, num_predictions + 1):
        prev_lat = latitudes[-1] if i == 1 else predicted_points[last_time + i - 1]['latitude']
        prev_long = longitudes[-1] if i == 1 else predicted_points[last_time + i - 1]['longitude']
        
        current_time += time_step
        next_lat = cs_lat(current_time)
        next_lon = cs_lon(current_time)
        
        # Estimate the date for the next point
        next_date = current_time

        print("-x1-", prev_lat,"\t-y1-", prev_long,"\t-x2-", next_lat,"\t-y2-", next_lon)
        
        # Calculate error margin distance (inverse of speed)
        current_speed = speeds[-1] if i == 1 else speeds[-1]  # Use the last known speed (or can use average speed)
        error_margin = base_error_step * (time_step / 5) / current_speed * i
        
        # Calculate perpendicular points
        perp_point1, perp_point2 = calculate_perpendicular(prev_lat, prev_long, next_lat, next_lon, i, 0.0001)

        print("prep : ", perp_point1, "\npoint", [next_lat, next_lon], "\nprep2 : ", perp_point2)
        
        predicted_points[last_time + i] = {
            'date': next_date,
            'latitude': next_lat,
            'longitude': next_lon,
            'perp_point1': {'latitude': perp_point1[0], 'longitude': perp_point1[1]},
            'perp_point2': {'latitude': perp_point2[0], 'longitude': perp_point2[1]},
            'vitesse': None,  # Speed not calculated in this approach
            'distance': None  # Distance not calculated in this approach
        }
    
    return predicted_points

def create_error_zone_recurence(polygon, predicted_points):
    if not predicted_points:
        return polygon
    ts, point = predicted_points.popitem()
    polygon.append((point['perp_point1']['longitude'], point['perp_point1']['latitude']))
    polygon = create_error_zone_recurence(polygon, predicted_points)
    polygon.append((point['perp_point2']['longitude'], point['perp_point2']['latitude']))

    return polygon

def create_error_zone_polygon(gps_data, predicted_points):
    timestamps = sorted(gps_data.keys())
    last_point = gps_data[timestamps[-1]]
    last_lat = last_point['latitude']
    last_lon = last_point['longitude']
    
    predicted_points = dict(reversed(sorted(predicted_points.items())))

    points = [(last_lon, last_lat)]
    points = create_error_zone_recurence(points, predicted_points)
    
    return Polygon(points)

# Example usage
gps_data = {
    1721836574.277: {'date': 1721836567.3032665, 'latitude': 16.051108820558086, 'longitude': 108.22507352428653, 'vitesse': 5},
    1721836584.277: {'date': 1721836577.3032665, 'latitude': 16.051108720558086, 'longitude': 108.22507372428653, 'vitesse': 1},
    1721836594.277: {'date': 1721836587.3032665, 'latitude': 16.051108520558086, 'longitude': 108.22507392428653, 'vitesse': 15}
}

gps_data_2 = {
    1721836574.277: {'date': 1721836567.3032665, 'latitude': 16.051104020558086, 'longitude': 108.22507400428653, 'vitesse': 5},
    1721836584.277: {'date': 1721836577.3032665, 'latitude': 16.051104320558086, 'longitude': 108.22507412428653, 'vitesse': 1},
    1721836594.277: {'date': 1721836587.3032665, 'latitude': 16.051104820558086, 'longitude': 108.22507422428653, 'vitesse': 1}
}

predicted_points = predict_next_points(gps_data)
error_zone_polygon = create_error_zone_polygon(gps_data, predicted_points)
predicted_points_2 = predict_next_points(gps_data_2)
error_zone_polygon_2 = create_error_zone_polygon(gps_data_2, predicted_points_2)

print(error_zone_polygon.intersects(error_zone_polygon_2))
# Plotting the original and predicted trajectories
plt.figure(figsize=(10, 6))

# Original trajectory
latitudes = [gps_data[ts]['latitude'] for ts in sorted(gps_data.keys())]
longitudes = [gps_data[ts]['longitude'] for ts in sorted(gps_data.keys())]
plt.plot(longitudes, latitudes, 'go-', label='Original Trajectory')
latitudes_2 = [gps_data_2[ts]['latitude'] for ts in sorted(gps_data_2.keys())]
longitudes_2 = [gps_data_2[ts]['longitude'] for ts in sorted(gps_data_2.keys())]
plt.plot(longitudes_2, latitudes_2, 'yo-', label='Original Trajectory 2')

# Predicted trajectory
# pred_latitudes = [predicted_points[ts]['latitude'] for ts in sorted(predicted_points.keys())]
# pred_longitudes = [predicted_points[ts]['longitude'] for ts in sorted(predicted_points.keys())]
# plt.plot(pred_longitudes, pred_latitudes, 'bo-', label='Predicted Trajectory')
# pred_latitudes_2 = [predicted_points_2[ts]['latitude'] for ts in sorted(predicted_points_2.keys())]
# pred_longitudes_2 = [predicted_points_2[ts]['longitude'] for ts in sorted(predicted_points_2.keys())]
# plt.plot(pred_longitudes_2, pred_latitudes_2, 'ro-', label='Predicted Trajectory 2')

# Predicted error zones
error_zone_x, error_zone_y = error_zone_polygon.exterior.xy
plt.plot(error_zone_x, error_zone_y, 'b--', label='Predicted Error Zone')
error_zone_x_2, error_zone_y_2 = error_zone_polygon_2.exterior.xy
plt.plot(error_zone_x_2, error_zone_y_2, 'r--', label='Predicted Error Zone 2')

plt.xlabel('Longitude')
plt.ylabel('Latitude')
plt.axis('equal')
plt.title('Trajectory Prediction and Error Zones')
plt.grid(True)
plt.show()
