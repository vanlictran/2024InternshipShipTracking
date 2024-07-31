import paho.mqtt.client as paho
from prometheus_client import Gauge, Enum, CollectorRegistry, push_to_gateway
from shapely.geometry import Point, Polygon
import json
import urllib.request
import urllib.parse
import time
import threading
import math

DEBUG = True

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

# Function to check if a GPS point is in a zone area
def check_zone_area(lat, lon):
    # Get geojson file from 127.0.0.1:3030/data/zone-han-river.geojson
    with urllib.request.urlopen('http://127.0.0.1:3030/data/zone-han-river.geojson') as url:
        data = json.loads(url.read().decode())

    # Extract the coordinates of the polygon and round them
    polygon_coordinates = data['features'][0]['geometry']['coordinates'][0]
    rounded_polygon_coordinates = round_coordinates(polygon_coordinates)

    # Create a Point and Polygon object
    point = Point(lon, lat)  # Note: Point takes (x, y) which corresponds to (lon, lat)
    polygon = Polygon(rounded_polygon_coordinates)

    return 1 if (polygon.contains(point) or polygon.within(point)) else 3

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
        url = f'http://localhost:9090/api/v1/query?query={encoded_query}'
        response = urllib.request.urlopen(url).read().decode()
        return json.loads(response)['data']['result']
    except Exception as e:
        print(f"Failed to fetch data for query {query}: {e}")
        return []

def organize_data(data, metric_name, devices_data):
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


def calculate_direction(lat1, lon1, lat2, lon2):
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    magnitude = math.sqrt(delta_lat**2. + delta_lon**2.)
    direction = {'x': delta_lat / magnitude,'y': delta_lon / magnitude} if magnitude != .0 else {'x':.0,'y': .0}
    return direction

def check_devices_in_zone(device_id, devices_data, zones_alerts_polygon):
    poly_alert = -1
    current_device_data = devices_data[device_id]
    for d_id in devices_data.keys():
        if(device_id != d_id):
            for zone, lvl_alert in zones_alerts_polygon:
                if len(devices_data[d_id]) > 0:
                    if lvl_alert < poly_alert:
                        break
                    c_device = devices_data[d_id]
                    max_timestamp = max(c_device.keys())
                    position = Point(c_device[max_timestamp]['longitude'], c_device[max_timestamp]['latitude'])
                    if zone.contains(position):
                        poly_alert = lvl_alert
                        break
    return poly_alert

def data_merge_collision(last_data_device):
    device = last_data_device["device_id"]
    try:
        date_query = 'date[10m]'
        latitude_query = 'latitude[10m]'
        longitude_query = 'longitude[10m]'

        date_data = fetch_prometheus_data(date_query)
        latitude_data = fetch_prometheus_data(latitude_query)
        longitude_data = fetch_prometheus_data(longitude_query)

        devices_data = {}

        organize_data(date_data, 'date', devices_data)
        organize_data(latitude_data, 'latitude', devices_data)
        organize_data(longitude_data, 'longitude', devices_data)

        for device_id, data in devices_data.items():
            sorted_timestamps = sorted(data.keys(), reverse=True)[:2]
            devices_data[device_id] = {ts: data[ts] for ts in sorted_timestamps}

        #for current device, replace last position by the position in device and the previous one by the last position in the query

        if(device not in devices_data):
            Exception(f"Device {device} not found in devices data")
        current_device_data = devices_data[device]
        current_device_timestamps = sorted(current_device_data.keys(), reverse=True)
        devices_data[device] = {current_device_timestamps[0]+1: {'date': last_data_device["date"], 'latitude': last_data_device["latitude"], 'longitude': last_data_device["longitude"]},
                                    current_device_timestamps[0]: current_device_data[current_device_timestamps[0]]}
        current_device_latest_date = last_data_device["date"]

        devices_registered = {}

        for device_id, data in devices_data.items():
            for timestamp, values in data.items():
                if abs(values["date"] - current_device_latest_date) < 600:
                    devices_registered[device_id] = data
                    break

        devices_data = devices_registered

        direction_data = {}

        for device_id, data in devices_data.items():
            if len(data) > 1:
                latest_timestamp = max(data.keys())
                previous_timestamp = min(data.keys())
                lat1 = data[previous_timestamp]['latitude']
                lon1 = data[previous_timestamp]['longitude']
                lat2 = data[latest_timestamp]['latitude']
                lon2 = data[latest_timestamp]['longitude']
                direction = calculate_direction(lat1, lon1, lat2, lon2)
                direction_data[device_id] = direction

        return devices_data, direction_data
    except Exception as e:
        print(f"Failed to merge collision data: {e}")
        return {}, {}

def data_merge_zones():
    zones = []
    urls = ['http://127.0.0.1:3030/data/zone-close-ship.json']
    for url in urls:
        data = fetch_geojson_from_url(url)
        if data:
            zones.append((data['pos'], data['level_alert']))
    return zones if zones else None

def zone_orientation(direction, dimension, point):
    if direction['x'] == 0 and direction['y'] == 0:
        return None
    if dimension is None:
        return None
    
    vecteur_orthogonal = {'x': -direction['y'], 'y': direction['x']}
    
    l2 = dimension["long"]
    l = dimension["larg"]
    
    x = point.x
    y = point.y
    
    norme_dir = math.sqrt(direction['x']**2 + direction['y']**2)
    norme_orthogonal = math.sqrt(vecteur_orthogonal['x']**2 + vecteur_orthogonal['y']**2)
    
    vecteur_orthogonal['x'] /= norme_orthogonal
    vecteur_orthogonal['y'] /= norme_orthogonal
    
    direction['x'] /= norme_dir
    direction['y'] /= norme_dir

    P1 = (x + l2 * vecteur_orthogonal['x'], y + l2 * vecteur_orthogonal['y'])
    P2 = (x - l2 * vecteur_orthogonal['x'], y - l2 * vecteur_orthogonal['y'])
    P3 = (P1[0] + l * direction['x'], P1[1] + l * direction['y'])
    P4 = (P2[0] + l * direction['x'], P2[1] + l * direction['y'])
    
    final_zone = Polygon([P1, P2, P4, P3])
    return final_zone

def check_collision(device):
    device_id = device["device_id"]
    try:
        devices_data, direction = data_merge_collision(device)
        if not devices_data:
            Exception("No data found for devices")
        if not direction:
            Exception("No direction found for devices")
        if device_id not in direction:
            Exception(f"No direction found for device {device_id}")
        if device_id not in devices_data:
            Exception(f"No data found for device {device_id}")

        zones_polygon = data_merge_zones()
        if zones_polygon is None:
            return 0
        max_timestamp = max(devices_data[device_id].keys())
        position = Point(devices_data[device_id][max_timestamp]['longitude'], devices_data[device_id][max_timestamp]['latitude'])

        oriented_zones = []
        for zone, level in zones_polygon:
            oriented_zones.append((zone_orientation(direction[device_id], zone, position), level))

        oriented_zones = [(x,y) for x, y in oriented_zones if x is not None]
        return check_devices_in_zone(device_id, devices_data, oriented_zones)
    except Exception as e:
        print(f"Failed to check collision: {e}")
        return 0

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
        
        previous_data = json.loads(urllib.request.urlopen('http://localhost:9090/api/v1/query?query={device_id="' + device_id + '"}').read().decode())

        previous_data = previous_data['data']['result']

        prev_values = {item['metric']['__name__']: item['value'][1] for item in previous_data}
    
        distance, speed = calculate_distance_speed(object_data, prev_values, current_time)
        
        state = check_zone_area(object_data['latitude'], object_data['longitude'])

        object_data['speed'] = speed
        object_data['distance'] = distance
        object_data['date'] = current_time
        object_data['collision_detection']= check_collision(object_data) if STATE_LIST[state] in MOVING_STATUT_LIST else 0

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
        push_to_gateway('localhost:9091', job='data-ship', registry=registry)
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

def calculate_distance_speed(data, prev_values, current_time):
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
    
def debug_send_data():
    STATE_LIST = ['DOWN', 'MOVING', 'STAND BY', 'OUT OF RANGE']
    MOVING_STATUT_LIST = set(['MOVING', 'OUT OF RANGE'])

    points = [
    (108.22507352428653, 16.051108320558086),
    (108.22639971227449, 16.05155141920838),
    (108.22709162007897, 16.050886534228567),
    (108.22789889108918, 16.050443229611872),
    # (108.22870618439805, 16.04972288399783),
    # (108.22951340179026, 16.04927959864436),
    # (108.22962870804628, 16.048226880814326),
    # (108.22980158606742, 16.04739583621911),
    # (108.23049350496632, 16.04794984888244),
    # (108.23055115809495, 16.048947162036157),
    # (108.2302628924541, 16.049778252515623),
    # (108.22928278927805, 16.05072015086779),
    # (108.22812909310721, 16.051440666019417),
    # (108.22680327037625, 16.05188383557885),
    # (108.2271492385691, 16.052825664978528),
    # (108.22761048956158, 16.053601297069534),
    # (108.22847520434664, 16.053712112696132),
    # (108.2295128182173, 16.053601325100942),
    # (108.22951290762137, 16.054543153522175),
    # (108.22951296547171, 16.055152576551066),
    # (108.22916717925841, 16.056094420058145),
    # (108.22859095174147, 16.056925487465264),
    # (108.22795676733239, 16.05742412218885),
    # (108.22732258292456, 16.058144370141505),
    # (108.22686135790025, 16.058698405254347),
    # (108.22588109064799, 16.059196975046135),
    # (108.22547715363879, 16.059806229968004),
    # (108.22547714684606, 16.06074802017993),
    # (108.22490030747252, 16.06119099009676),
    # (108.22478511113934, 16.060138496266703),
    # (108.22484331037896, 16.05897534918232),
    # (108.22490096957654, 16.057811904000275),
    # (108.22455504249575, 16.056925460574178),
    # (108.22443974030688, 16.05581740582862),
    # (108.22467015177398, 16.0544323625289),
    # (108.22495815953454, 16.05260418566847)
    ]

    points_2 = [
    (108.22507352428653, 16.051108320558086),
    (108.22639971227449, 16.05155141920838),
    (108.22709162007897, 16.050886534228567),
    (108.22789889108918, 16.050443229611872),
    # (108.22870618439805, 16.04972288399783),
    # (108.22951340179026, 16.04927959864436),
    # (108.22962870804628, 16.048226880814326),
    # (108.22980158606742, 16.04739583621911),
    # (108.23049350496632, 16.04794984888244),
    # (108.23055115809495, 16.048947162036157),
    # (108.2302628924541, 16.049778252515623),
    # (108.22928278927805, 16.05072015086779),
    # (108.22812909310721, 16.051440666019417),
    # (108.22680327037625, 16.05188383557885),
    # (108.2271492385691, 16.052825664978528),
    # (108.22761048956158, 16.053601297069534),
    # (108.22847520434664, 16.053712112696132),
    # (108.2295128182173, 16.053601325100942),
    # (108.22951290762137, 16.054543153522175),
    # (108.22951296547171, 16.055152576551066),
    # (108.22916717925841, 16.056094420058145),
    # (108.22859095174147, 16.056925487465264),
    # (108.22795676733239, 16.05742412218885),
    # (108.22732258292456, 16.058144370141505),
    # (108.22686135790025, 16.058698405254347),
    # (108.22588109064799, 16.059196975046135),
    # (108.22547715363879, 16.059806229968004),
    # (108.22547714684606, 16.06074802017993),
    # (108.22490030747252, 16.06119099009676),
    # (108.22478511113934, 16.060138496266703),
    # (108.22484331037896, 16.05897534918232),
    # (108.22490096957654, 16.057811904000275),
    # (108.22455504249575, 16.056925460574178),
    # (108.22443974030688, 16.05581740582862),
    # (108.22467015177398, 16.0544323625289),
    # (108.22495815953454, 16.05260418566847)
    ]

    devices = ['debug_device', 'debug_device_2']

    step = 0
    #device_id = 'debug_device'
    while DEBUG:
        #try:
            for device_id in devices:
                current_time = time.time()
                # Get data from Prometheus limited to 1 and to the device ID
                previous_data = json.loads(urllib.request.urlopen('http://localhost:9090/api/v1/query?query={device_id="' + device_id + '"}').read().decode())

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
                    'latitude': points[step][1] if device_id == 'debug_device' else points_2[step][1], 
                    'longitude': points[step][0] if device_id == 'debug_device' else points_2[step][0],
                    'speed': 0.0,
                    'distance': 0.0,
                    'date': current_time,
                }

                distance, speed = calculate_distance_speed(object_data, prev_values, current_time)
                state = check_zone_area(object_data['latitude'], object_data['longitude'])

                object_data['speed'] = speed
                object_data['distance'] = distance

                object_data['collision_detection']= check_collision(object_data)

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
                
                push_to_gateway('localhost:9091', job='data-ship', registry=registry)

                time.sleep(1)

                # Wait for 15 seconds before sending the next debug data
            step = (step + 1) % len(points)
            time.sleep(15)
        # except Exception as e:
        #     print(f"Failed to send debug data: {e}")

if __name__ == '__main__':
    # Test Pushgateway connection before starting the MQTT client
    try:
        urllib.request.urlopen('http://localhost:9091/metrics')
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
