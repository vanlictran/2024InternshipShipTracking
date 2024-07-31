from shapely.geometry import Point, Polygon
import json
import urllib.request
import matplotlib.pyplot as plt

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

    return 1 if (polygon.contains(point) or polygon.within(point))==True else 3

if __name__ == "__main__":
    # Test with coordinates
    print(check_zone_area(16.071923, 108.226882))
    print(check_zone_area(16.071912, 108.221872))
