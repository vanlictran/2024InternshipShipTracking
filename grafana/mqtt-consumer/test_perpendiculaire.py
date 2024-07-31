import matplotlib.pyplot as plt
import numpy as np

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

def calculate_perpendicular(lat1, lon1, lat2, lon2, scale_km=50):
    distance = haversine_distance(lat1, lon1, lat2, lon2)
    bearing = np.arctan2(lon2 - lon1, lat2 - lat1)

    # Calculer le vecteur perpendiculaire (en radians)
    perp_bearing1 = bearing + np.pi / 2
    perp_bearing2 = bearing - np.pi / 2

    # Calculer les points de la perpendiculaire
    perp_point1 = move_point(lat2, lon2, scale_km, perp_bearing1)
    perp_point2 = move_point(lat2, lon2, scale_km, perp_bearing2)

    return perp_point1, perp_point2

def plot_segment_with_perpendicular(lat1, lon1, lat2, lon2, scale_km=50):
    # Calculer les points de la perpendiculaire
    perp_point1, perp_point2 = calculate_perpendicular(lat1, lon1, lat2, lon2, scale_km)
    
    # Tracer le segment et sa perpendiculaire
    plt.figure()
    plt.plot([lon1, lon2], [lat1, lat2], 'bo-', label='Segment')
    plt.plot([lon2, perp_point1[1]], [lat2, perp_point1[0]], 'r--', label='Perpendiculaire')
    plt.plot([lon2, perp_point2[1]], [lat2, perp_point2[0]], 'r--')
    plt.scatter(lon2, lat2, color='g', zorder=5, label='Deuxième point')
    plt.legend()
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.title('Segment et sa perpendiculaire au deuxième point (coordonnées géographiques)')
    plt.grid(True)
    plt.axis('equal')
    plt.show()

# Exemple d'utilisation
lat1, lon1 = 48.8566, 2.3522  # Paris
lat2, lon2 = 51.5074, -0.1278  # Londres
plot_segment_with_perpendicular(lat1, lon1, lat2, lon2, scale_km=50)
