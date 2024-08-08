import paho.mqtt.client as paho
from prometheus_client import Gauge, Enum, CollectorRegistry, push_to_gateway
from scipy.interpolate import CubicSpline
from shapely.geometry import Point, Polygon
import json
import urllib.request as requests
import urllib.parse
import time
import threading
import math
import numpy as np
import matplotlib.pyplot as plt

DEBUG = False


PUSHGATEWAY = 'http://pushgateway:9091'
PROMETHEUS = 'http://prometheus:9090'
NGINX = 'http://nginx:3030'
if DEBUG:
    PUSHGATEWAY = 'http://localhost:4447'
    PROMETHEUS = 'http://localhost:4444'
    NGINX = 'http://localhost:3030'

# table of state usable in thread function
STATE_LIST = ['DOWN', 'MOVING', 'STAND BY', 'OUT OF RANGE']
MOVING_STATUT_LIST = ['MOVING', 'OUT OF RANGE']

# Define Prometheus metrics for the values in the "object"
registry = CollectorRegistry()
ACCELERATION_X_METRIC = Gauge('sensor_acceleration_x', 'Acceleration X from sensor', ['device_id'], registry=registry)
ACCELERATION_Y_METRIC = Gauge('sensor_acceleration_y', 'Acceleration Y from sensor', ['device_id'], registry=registry)
ACCELERATION_Z_METRIC = Gauge('sensor_acceleration_z', 'Acceleration Z from sensor', ['device_id'], registry=registry)
BATTERY_METRIC = Gauge('sensor_battery', 'Battery level from sensor', ['device_id'], registry=registry)
LATITUDE_METRIC = Gauge('latitude', 'Latitude from sensor', ['device_id'], registry=registry)
LONGITUDE_METRIC = Gauge('longitude', 'Longitude from sensor', ['device_id'], registry=registry)
TEMPERATURE_METRIC = Gauge('sensor_temperature', 'Temperature from sensor', ['device_id'], registry=registry)
STATUT_METRIC = Gauge('statut', 'Statut boat', ['device_id'], registry=registry)
STATUT_NAME_METRIC = Enum('statut_name', 'Statut boat', labelnames=['device_id'], states=STATE_LIST, registry=registry)
SPEED_METRIC = Gauge('speed', 'Speed from sensor', ['device_id'], registry=registry)
DISTANCE_METRIC = Gauge('distance', 'Distance from sensor', ['device_id'], registry=registry)
DATE_METRIC = Gauge('date', 'Date from sensor', ['device_id'], registry=registry)
COLLISON_DETECTION_METRIC = Gauge('collison_detection', 'Collison detection from sensor', ['device_id'], registry=registry)


# Function to round coordinates to 7 decimal places
def round_coordinates(coordinates, precision=7):
    return [[round(coord[0], precision), round(coord[1], precision)] for coord in coordinates]


#############################################################################################
#                                    STATE CALCULATION                                      #
#############################################################################################

# Function to check if a GPS point is in a zone area
def check_position_area(lat, lon):
    # Get geojson file from 127.0.0.1:3030/data/zone-han-river.geojson
    with urllib.request.urlopen(NGINX + '/data/zone-han-river.geojson') as url:
        data = json.loads(url.read().decode())

    # Extract the coordinates of the polygon and round them
    polygon_coordinates = data['features'][0]['geometry']['coordinates'][0]
    rounded_polygon_coordinates = round_coordinates(polygon_coordinates)

    # Create a Point and Polygon object
    point = Point(lon, lat)  # Note: Point takes (x, y) which corresponds to (lon, lat)
    polygon = Polygon(rounded_polygon_coordinates)

    return 1 if (polygon.contains(point) or polygon.within(point)) else 3

def check_state(current_device_data, data):
    print(current_device_data)
    return 2 if not(is_moving_noise_reduction(current_device_data, data)) else check_position_area(current_device_data['latitude'], current_device_data['longitude'])

def is_moving_noise_reduction(current, data, threshold_avg = 15, threshold_far=35, num_points=5):
    data = list(data.values())
    if len(data) == 0:
        return False

    lon_current = current["longitude"]
    lat_current = current["latitude"]

    total_distance = 0
    farest_point = 0
    if(len(data) == 0):
        return False
    for i in range(0, min(num_points, len(data))):
        lon_prev = data[i]["longitude"]
        lat_prev = data[i]["latitude"]
        distance = haversine_distance_in_meters(lon_current, lat_current, lon_prev, lat_prev)
        print(distance)
        if distance > farest_point:
            farest_point = distance
        total_distance += distance
    print('############################################################\n', farest_point, total_distance,'\n############################################################')
    average_distance = total_distance / num_points
    return True if farest_point > threshold_far else False if average_distance < threshold_avg else True

#############################################################################################
#                                      FETCHING DATA                                        #
#############################################################################################

def fetch_geojson_from_url(url):
    try:
        with urllib.request.urlopen(url) as response:
            geojson_data = json.loads(response.read().decode())
        return geojson_data
    except Exception as e:
        print(f"Failed to fetch GeoJSON data from URL {url}: {e}")
        return None

def fetch_prometheus_data(query):
    try:
        encoded_query = urllib.parse.quote(query)
        url = PROMETHEUS + '/api/v1/query?query='+ encoded_query
        response = urllib.request.urlopen(url).read().decode()
        return json.loads(response)['data']['result']
    except Exception as e:
        print(f"Failed to fetch data for query {query}: {e}")
        return []

def organize_data(data, metric_name, devices_data):
    # print("--------")
    # print(data)
    # print("--------\n")
    for entry in data:
        metric = entry['metric']
        device_id = metric['device_id']
        values = entry['values']
        if device_id not in devices_data:
            devices_data[device_id] = {}

        for value in values:
            timestamp, val = value
            if timestamp not in devices_data[device_id]:
                devices_data[device_id][timestamp] = {}
            devices_data[device_id][timestamp][metric_name] = float(val)
    return devices_data

def reduce_duplicates(data):
    seen = set()
    new = {}
    for k, v in data.items():
        if v["date"] not in seen:
            new[k] = v
            seen.add(v["date"])
    del seen
    return new

def data_merging(last_data_device):
    DATA_QUERY = '{job="data-ship"}[2m]'
    device = last_data_device['device_id']
    try:
        date_query = 'date'+DATA_QUERY
        latitude_query = 'latitude'+DATA_QUERY
        longitude_query = 'longitude'+DATA_QUERY
        speed_query = 'speed'+DATA_QUERY

        date_data = fetch_prometheus_data(date_query)
        latitude_data = fetch_prometheus_data(latitude_query)
        longitude_data = fetch_prometheus_data(longitude_query)
        speed_data = fetch_prometheus_data(speed_query)

        devices_data = {}
        devices_data = organize_data(date_data, 'date', devices_data)
        devices_data = organize_data(latitude_data, 'latitude', devices_data)
        devices_data = organize_data(longitude_data, 'longitude', devices_data)
        devices_data = organize_data(speed_data, 'speed', devices_data)

        devices_data = {device_id: reduce_duplicates(data) for device_id, data in devices_data.items()}

        for device_id, data in devices_data.items():
            sorted_timestamps = sorted(data.keys(), reverse=True)
            devices_data[device_id] = {ts: data[ts] for ts in sorted_timestamps}

        if(device not in devices_data):
            Exception(f"Device {device} not found in devices data")

        print(devices_data)

        current_device_data = devices_data[device]
        current_device_timestamps = sorted(current_device_data.keys(), reverse=True)
        devices_data[device][current_device_timestamps[0]+1] = {
            'date': last_data_device["date"],
            'latitude': last_data_device["latitude"],
            'longitude': last_data_device["longitude"],
            'speed': last_data_device["speed"]
        }
        devices_data[device].pop(current_device_timestamps[-1])
        current_device_latest_date = last_data_device["date"]
        
        return devices_data
    except Exception as e:
        print(f"Failed to merge collision data: {e}")
        return {}

#############################################################################################
#                                   PREDICTION MOVEMENT                                     #
#############################################################################################

def haversine_distance_in_meters(lat1, lon1, lat2, lon2):
    return haversine_distance(lat1, lon1, lat2, lon2) * 1000

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

def calculate_perpendicular(lat1, lon1, lat2, lon2, scale_km=0.05):
    distance = haversine_distance(lat1, lon1, lat2, lon2)
    bearing = math.atan2(lon2 - lon1, lat2 - lat1)

    # Calculer le vecteur perpendiculaire (en radians)
    perp_bearing1 = bearing + math.pi / 2
    perp_bearing2 = bearing - math.pi / 2

    # Calculer les points de la perpendiculaire
    perp_point1 = move_point(lat2, lon2, scale_km, perp_bearing1)
    perp_point2 = move_point(lat2, lon2, scale_km, perp_bearing2)

    return perp_point1, perp_point2

def predict_next_points(gps_data, num_predictions=3, time_step=20, base_error_step=0.02):

    try:
        seen = set()
        # delete entries that have same values in gps_data
        new = {}
        for k, v in gps_data.items():
            if v["date"] not in seen:
                new[k] = v
                seen.add(v["date"])
        del seen

        gps_data = new
        del new

        if(gps_data.__len__() < 2):
            return {}

        timestamps = sorted(gps_data.keys())
        last_point = gps_data[timestamps[-1]]
        
        # Extract latitudes, longitudes, times, and speeds
        latitudes = [gps_data[ts]['latitude'] for ts in timestamps]
        longitudes = [gps_data[ts]['longitude'] for ts in timestamps]
        times = [gps_data[ts]['date'] for ts in timestamps]
        speeds = [gps_data[ts]['speed'] for ts in timestamps]
        
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
            
            # Calculate error margin distance (inverse of speed)
            current_speed = speeds[-1] if i == 1 else speeds[-1]  # Use the last known speed (or can use average speed)
            # error_margin = base_error_step
            error_margin = base_error_step * (time_step / 5) / current_speed * i if current_speed != 0 else 0.000001
            
            # Calculate perpendicular points
            perp_point1, perp_point2 = calculate_perpendicular(prev_lat, prev_long, next_lat, next_lon, error_margin)
            
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
    except Exception as e:
        print(f"Failed to predict next points: {e}")
        return {}

def create_error_zone_recurence(polygon, predicted_points):
    if predicted_points == {}:
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

def check_collision(current_device_id, devices_data):
    devices_data = devices_data
    current_zone = {}
    zones = []

    for device_id, data in devices_data:
        predicted_points = predict_next_points(data)
        if predicted_points == {}:
            break
        # get first data of the device
        error_zone_polygon = create_error_zone_polygon(data, predicted_points)
        if(device_id == current_device_id):
            current_zone = error_zone_polygon
        else:
            zones.append(error_zone_polygon)

    for zone in zones:
        if zone.intersects(current_zone):
            # DEBUG
            # plot_trajectories(current_zone, zones)
            return 1

    return 0

#############################################################################################
#                                           DEBUG                                           #
#############################################################################################

# function to vizualize the trajectory and the error zones on a map (in a thread, to avoid blocking the main thread, and killed when new information is available)
def plot_trajectories(current_zone, zones):
    # Plotting the original and predicted trajectories
    plt.figure(figsize=(10, 10))

    # Original trajectory
    x, y = current_zone.exterior.xy

    plt.plot(x, y, 'g--', label='Original Trajectory')
    plt.fill(x, y, 'g', alpha=0.3)

    for zone in zones:
        x, y = zone.exterior.xy
        plt.plot(x, y, 'r--', label='Error Zone')
        plt.fill(x, y, 'r', alpha=0.3)
        print("zone")

    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.title('Trajectories and error zones')
    plt.grid(True)
    plt.axis('equal')
    plt.show()

def debug_send_data():
    STATE_LIST = ['DOWN', 'MOVING', 'STAND BY', 'OUT OF RANGE']
    MOVING_STATUT_LIST = set(['MOVING', 'OUT OF RANGE'])

    points = [
    (108.22507352428653, 16.051108320558086),
    (108.22639971227449, 16.05155141920838),
    (108.22709162007897, 16.050886534228567),
    (108.22789889108918, 16.050443229611872),
    (108.22870618439805, 16.04972288399783),
    (108.22951340179026, 16.04927959864436),
    (108.22962870804628, 16.048226880814326),
    (108.22980158606742, 16.04739583621911),
    (108.23049350496632, 16.04794984888244),
    (108.23055115809495, 16.048947162036157),
    (108.2302628924541, 16.049778252515623),
    (108.22928278927805, 16.05072015086779),
    (108.22812909310721, 16.051440666019417),
    (108.22680327037625, 16.05188383557885),
    (108.2271492385691, 16.052825664978528),
    (108.22761048956158, 16.053601297069534),
    (108.22847520434664, 16.053712112696132),
    (108.2295128182173, 16.053601325100942),
    (108.22951290762137, 16.054543153522175),
    (108.22951296547171, 16.055152576551066),
    (108.22916717925841, 16.056094420058145),
    (108.22859095174147, 16.056925487465264),
    (108.22795676733239, 16.05742412218885),
    (108.22732258292456, 16.058144370141505),
    (108.22686135790025, 16.058698405254347),
    (108.22588109064799, 16.059196975046135),
    (108.22547715363879, 16.059806229968004),
    (108.22547714684606, 16.06074802017993),
    (108.22490030747252, 16.06119099009676),
    (108.22478511113934, 16.060138496266703),
    (108.22484331037896, 16.05897534918232),
    (108.22490096957654, 16.057811904000275),
    (108.22455504249575, 16.056925460574178),
    (108.22443974030688, 16.05581740582862),
    (108.22467015177398, 16.0544323625289),
    (108.22495815953454, 16.05260418566847)
    ]

    devices = ['debug_device', 'debug_device_2']

    step = 0
    #device_id = 'debug_device'
    while DEBUG:
        try:
            for device_id in devices:
                current_time = time.time()
                # Get data from Prometheus limited to 1 and to the device ID
                previous_data = json.loads(urllib.request.urlopen(PROMETHEUS + '/api/v1/query?query={device_id="' + device_id + '"}').read().decode())

                previous_data = previous_data['data']['result']

                prev_values = {item['metric']['__name__']: item['value'][1] for item in previous_data}

                # Simulated object data for debugging
                object_data = {
                    'device_id': device_id,
                    'acceleration_x': 0.0,
                    'acceleration_y': 0.0,
                    'acceleration_z': 0.0,
                    'battery': 100.0,
                    'temperature': 25.0,
                    'latitude': points[step][1] if device_id == 'debug_device' else 16.051108320558086, 
                    'longitude': points[step][0] if device_id == 'debug_device' else 108.22507352428653,
                    'speed': 0.0,
                    'distance': 0.0,
                    'date': current_time,
                }

                distance, speed = calculate_distance_speed(object_data, prev_values, current_time)

                object_data['device_id'] = device_id
                object_data['speed'] = speed
                object_data['distance'] = distance

                datas = data_merging(object_data)

                object_data['collision_detection']= check_collision(device_id, datas.items())
                all_datas = datas[device_id] if device_id in datas else {}
                state = check_state(object_data, all_datas)

                # Update Prometheus metrics
                ACCELERATION_X_METRIC.labels(device_id=device_id).set(object_data['acceleration_x'])
                ACCELERATION_Y_METRIC.labels(device_id=device_id).set(object_data['acceleration_y'])
                ACCELERATION_Z_METRIC.labels(device_id=device_id).set(object_data['acceleration_z'])
                BATTERY_METRIC.labels(device_id=device_id).set(object_data['battery'])
                TEMPERATURE_METRIC.labels(device_id=device_id).set(object_data['temperature'])

                LATITUDE_METRIC.labels(device_id=device_id).set(object_data['latitude'])
                LONGITUDE_METRIC.labels(device_id=device_id).set(object_data['longitude'])
                STATUT_METRIC.labels(device_id=device_id).set(state)
                STATUT_NAME_METRIC._labelnames = ['device_id']
                STATUT_NAME_METRIC._states = STATE_LIST
                STATUT_NAME_METRIC.labels(device_id=device_id).state(STATE_LIST[state])
                SPEED_METRIC.labels(device_id=device_id).set(object_data['speed'])
                DISTANCE_METRIC.labels(device_id=device_id).set(object_data['distance'])

                DATE_METRIC.labels(device_id=device_id).set(object_data['date'])
                COLLISON_DETECTION_METRIC.labels(device_id=device_id).set(object_data['collision_detection'])

                print(f"Debug data sent: {object_data}")

                
                # Push metrics to Prometheus Pushgateway with the job name 'mqtt_listener'
                
                push_to_gateway(PUSHGATEWAY, job='data-ship', registry=registry)

                time.sleep(2)

                # Wait for 15 seconds before sending the next debug data
            step = (step + 1) % len(points)
            # time.sleep(15)
        except Exception as e:
            print(f"Failed to send debug data: {e}")


#############################################################################################
#                               CLIENT FUNCTION DEFINITION                                  #
#############################################################################################

def on_message(mosq, obj, msg):
    try:
        current_time = time.time()
        # Parse the JSON payload
        payload = json.loads(msg.payload.decode())

        # Extract device ID
        device_id = payload['devEUI']

        # Extract the object data
        object_data = payload['object']

        # Get data from Prometheus limited to 1 and to the device ID
        
        previous_data = json.loads(urllib.request.urlopen(PROMETHEUS + '/api/v1/query?query={device_id="' + device_id + '"}').read().decode())

        previous_data = previous_data['data']['result']

        prev_values = {item['metric']['__name__']: item['value'][1] for item in previous_data}
    
        distance, speed = calculate_distance_speed(object_data, prev_values, current_time)
        
        state = check_state(object_data['latitude'], object_data['longitude'])


        object_data['device_id'] = device_id
        object_data['speed'] = speed
        object_data['distance'] = distance
        object_data['date'] = current_time
        object_data['collision_detection']= check_collision(object_data)

        # Update Prometheus metrics
        ACCELERATION_X_METRIC.labels(device_id=device_id).set(object_data['acceleration_x'])
        ACCELERATION_Y_METRIC.labels(device_id=device_id).set(object_data['acceleration_y'])
        ACCELERATION_Z_METRIC.labels(device_id=device_id).set(object_data['acceleration_z'])
        BATTERY_METRIC.labels(device_id=device_id).set(object_data['battery'])
        TEMPERATURE_METRIC.labels(device_id=device_id).set(object_data['temperature'])
        STATUT_METRIC.labels(device_id=device_id).set(state)
        STATUT_NAME_METRIC.labels(device_id=device_id).state(STATE_LIST[state])
        SPEED_METRIC.labels(device_id=device_id).set(object_data['speed'])
        DISTANCE_METRIC.labels(device_id=device_id).set(object_data['distance'])
        DATE_METRIC.labels(device_id=device_id).set(object_data['date'])
        LATITUDE_METRIC.labels(device_id=device_id).set(object_data['latitude'])
        LONGITUDE_METRIC.labels(device_id=device_id).set(object_data['longitude'])
        COLLISON_DETECTION_METRIC.labels(device_id=device_id).set(object_data['collision_detection'])

        print(f"Received data from {device_id}: {object_data}")

        # Push metrics to Prometheus Pushgateway with the job name 'mqtt_listener'
        push_to_gateway(PUSHGATEWAY, job='data-ship', registry=registry)
    except json.JSONDecodeError as e:
        print(f"Failed to decode JSON payload: {e}")
    except KeyError as e:
        print(f"Missing key in JSON payload: {e}")
    except Exception as e:
        print(f"Failed to push metrics to Pushgateway: {e}")

def on_publish(mosq, obj, mid):
    pass

def read_endpoints(file_path):
    with open(file_path, 'r') as file:
        topics = file.readlines()
    return [topic.strip() for topic in topics]

def connect_mqtt(client):
    while True:
        try:
            client.connect("vngalaxy.vn", 1883, 60)
            print("Connected to MQTT broker.")
            break
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}. Retrying in 5 seconds...")
            time.sleep(5)

#############################################################################################
#                              SPEED & DISTANCE CALCULATION                                 #
#############################################################################################

def calculate_distance_speed(data, prev_values, current_time):
    print(data)
    print(prev_values)
    try:
        # Convert string values to float
        lat1, lon1 = float(prev_values['latitude']), float(prev_values['longitude'])
        lat2, lon2 = float(data['latitude']), float(data['longitude'])

        # Radius of the Earth in km
        R = 6371.0

        # Convert latitude and longitude from degrees to radians
        lat1 = math.radians(lat1)
        lon1 = math.radians(lon1)
        lat2 = math.radians(lat2)
        lon2 = math.radians(lon2)

        # Calculate the change in coordinates
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        # Haversine formula
        a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        distance = R * c

        # Calculate time difference in hours
        elapsed_time = (current_time - float(prev_values["date"])) / 3600.0

        print(f"Elapsed time: {elapsed_time} hours")

        # Calculate speed in km/h
        if elapsed_time > 0:
            speed = distance / elapsed_time
        else:
            speed = 0.0

        return distance, speed
    except Exception as e:
        print(f"Failed to calculate distance and speed: {e}")
        return 0.0, 0.0

#############################################################################################
#                                           MAIN                                            #
#############################################################################################

if __name__ == '__main__':
    # Test Pushgateway connection before starting the MQTT client
    print(f"Connecting to Pushgateway at {PUSHGATEWAY}...")
    print(f"Connecting to Prometheus at {PROMETHEUS}...")
    try:
        urllib.request.urlopen(PUSHGATEWAY+'/metrics')
        print("Pushgateway connection successful.")
    except Exception as e:
        print(f"Pushgateway connection failed: {e}")
        exit(1)

    client = paho.Client()
    client.on_message = on_message
    client.on_publish = on_publish

    # Read the device IDs from the file and subscribe to the appropriate topics
    device_ids = read_endpoints('endpoints.txt')

    connect_mqtt(client)  # Try to connect to the MQTT broker

    topic = "application/86/device/+/event/up"
    client.subscribe(topic, 2)
    # for device_id in device_ids:
    #     topic = f"application/86/device/{device_id}/event/up"
    #     client.subscribe(topic, 2)

    # Start the debug thread if DEBUG is set to True
    if DEBUG:
        debug_thread = threading.Thread(target=debug_send_data)
        debug_thread.daemon = True
        debug_thread.start()

    # Loop to process MQTT messages
    while True:
        try:
            client.loop_forever()
        except Exception as e:
            print(f"MQTT connection lost: {e}. Reconnecting...")
            connect_mqtt(client)
