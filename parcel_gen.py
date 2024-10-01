import numpy as np
import math

class ParcelGenerator:
    def __init__(self, area_corners, parcel_width_m, parcel_height_m, gap_x_m, gap_y_m, num_parcels_x, num_parcels_y, is_fit=True, colors=None):
        # Convert all coordinates to floats to ensure numeric operations work
        self.area_corners = [list(map(float, coord)) for coord in area_corners]
        self.parcel_width_m = float(parcel_width_m)
        self.parcel_height_m = float(parcel_height_m)
        self.gap_x_m = float(gap_x_m)
        self.gap_y_m = float(gap_y_m)
        self.num_parcels_x = int(num_parcels_x)
        self.num_parcels_y = int(num_parcels_y)
        self.is_fit = is_fit
        self.colors = colors if colors else ["#ff0000", "#008000", "#0000ff", "#ffff00", "#00ffff", "#ff00ff"]

    def haversine_distance(self, coord1, coord2):
        """Calculate the great-circle distance between two points on the Earth's surface in meters."""
        lat1, lon1 = np.radians(coord1[0]), np.radians(coord1[1])
        lat2, lon2 = np.radians(coord2[0]), np.radians(coord2[1])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat / 2.0) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2.0) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        # Earth's radius in meters
        R = 6371000  
        
        return R * c

    def move_point(self, start_lat, start_lng, distance, bearing):
        """Move a point a certain distance in a given bearing."""
        R = 6371000  # Earth's radius in meters
        lat1 = math.radians(start_lat)
        lon1 = math.radians(start_lng)

        lat2 = math.asin(math.sin(lat1) * math.cos(distance / R) +
                         math.cos(lat1) * math.sin(distance / R) * math.cos(bearing))

        lon2 = lon1 + math.atan2(math.sin(bearing) * math.sin(distance / R) * math.cos(lat1),
                                 math.cos(distance / R) - math.sin(lat1) * math.sin(lat2))

        return math.degrees(lat2), math.degrees(lon2)

    def generate_parcel_coordinates(self):
        # Get the corner coordinates
        top_left, top_right, bottom_right, bottom_left = [np.array(coord) for coord in self.area_corners]

        # Calculate the initial width and height using Haversine distance
        area_width_m = self.haversine_distance(top_left, top_right)
        area_height_m = self.haversine_distance(top_left, bottom_left)

        # Calculate the initial bearings (direction) for the top and left edges
        bearing_x = math.atan2(top_right[1] - top_left[1], top_right[0] - top_left[0])  # Bearing for the top edge
        bearing_y = math.atan2(bottom_left[1] - top_left[1], bottom_left[0] - top_left[0])  # Bearing for the left edge

        # If is_fit is enabled, adjust the parcel dimensions to fit the area
        if self.is_fit:
            total_parcel_width = self.num_parcels_x * (self.parcel_width_m + self.gap_x_m) - (self.gap_x_m if self.gap_x_m != 0 else 0)
            total_parcel_height = self.num_parcels_y * (self.parcel_height_m + self.gap_y_m) - (self.gap_y_m if self.gap_y_m != 0 else 0)

            scale_x = area_width_m / total_parcel_width
            scale_y = area_height_m / total_parcel_height

            scale_factor = min(scale_x, scale_y)

            self.parcel_width_m *= scale_factor
            self.parcel_height_m *= scale_factor
            
            # Only scale gaps if they are non-zero
            if self.gap_x_m != 0:
                self.gap_x_m *= scale_factor
            if self.gap_y_m != 0:
                self.gap_y_m *= scale_factor

        # Ensure gaps remain zero if they were initially set to zero
        self.gap_x_m = 0 if self.gap_x_m == 0 else self.gap_x_m
        self.gap_y_m = 0 if self.gap_y_m == 0 else self.gap_y_m

        # List to store the parcel coordinates
        parcels = []
        for j in range(self.num_parcels_y):
            for i in range(self.num_parcels_x):
                # Move to the origin of the current parcel
                move_x = i * (self.parcel_width_m + self.gap_x_m)
                move_y = j * (self.parcel_height_m + self.gap_y_m)

                parcel_origin_lat, parcel_origin_lng = self.move_point(top_left[0], top_left[1], move_x, bearing_x)
                parcel_origin_lat, parcel_origin_lng = self.move_point(parcel_origin_lat, parcel_origin_lng, move_y, bearing_y)

                # Calculate the corners of the parcel based on its width and height
                parcel_top_left = (parcel_origin_lat, parcel_origin_lng)
                parcel_top_right = self.move_point(parcel_origin_lat, parcel_origin_lng, self.parcel_width_m, bearing_x)
                parcel_bottom_right = self.move_point(parcel_top_right[0], parcel_top_right[1], self.parcel_height_m, bearing_y)
                parcel_bottom_left = self.move_point(parcel_origin_lat, parcel_origin_lng, self.parcel_height_m, bearing_y)

                # Assign color in a cycle through the provided colors list
                color = self.colors[(j * self.num_parcels_x + i) % len(self.colors)]

                # Store the parcel coordinates
                parcel = {
                    'coordinates': [
                        {"lat": parcel_top_left[0], "lng": parcel_top_left[1]},
                        {"lat": parcel_top_right[0], "lng": parcel_top_right[1]},
                        {"lat": parcel_bottom_right[0], "lng": parcel_bottom_right[1]},
                        {"lat": parcel_bottom_left[0], "lng": parcel_bottom_left[1]},
                    ],
                    'color': color
                }
                parcels.append(parcel)

        return parcels
