import numpy as np
import math

class ParcelGenerator:
    def __init__(
        self,
        area_corners,
        parcel_width_m,
        parcel_height_m,
        gap_x_m,
        gap_y_m,
        num_parcels_x,
        num_parcels_y,
        is_fit=True,
        preserve_parcel_size=False,
        colors=None
    ):
        """
        Constructor: Stores initial parameters but does not perform scaling.
        """
        # Convert all coordinates to floats to ensure numeric operations work
        self.area_corners = [list(map(float, coord)) for coord in area_corners]
        self.parcel_width_m = float(parcel_width_m)
        self.parcel_height_m = float(parcel_height_m)
        self.gap_x_m = float(gap_x_m)
        self.gap_y_m = float(gap_y_m)
        self.num_parcels_x = int(num_parcels_x)
        self.num_parcels_y = int(num_parcels_y)
        
        # If preserve_parcel_size is True, we definitely want to fit the area
        self.preserve_parcel_size = preserve_parcel_size
        if self.preserve_parcel_size:
            is_fit = True
        
        self.is_fit = is_fit
        
        # Default set of colors if none provided
        self.colors = colors if colors else [
            "#ff0000", "#008000", "#0000ff",
            "#ffff00", "#00ffff", "#ff00ff"
        ]

    @classmethod
    def create(
        cls,
        area_corners,
        parcel_width_m,
        parcel_height_m,
        gap_x_m,
        gap_y_m,
        num_parcels_x,
        num_parcels_y,
        is_fit=True,
        preserve_parcel_size=False,
        colors=None
    ):
        """
        Class method to create the generator, perform the fitting logic,
        and return both the new generator and updated gap values.
        """
        instance = cls(
            area_corners,
            parcel_width_m,
            parcel_height_m,
            gap_x_m,
            gap_y_m,
            num_parcels_x,
            num_parcels_y,
            is_fit,
            preserve_parcel_size,
            colors
        )

        # Fit parcels (this may change instance.gap_x_m and instance.gap_y_m)
        instance._fit_parcels()

        # Return the instance and the (possibly updated) gaps
        return instance, (instance.gap_x_m, instance.gap_y_m)

    def _fit_parcels(self):
        """
        Internal method:
          1) If is_fit=False: No scaling at all.
          2) If is_fit=True and preserve_parcel_size=False: 
             Scale both parcels and gaps to fit area.
          3) If is_fit=True and preserve_parcel_size=True:
             Keep parcel size the same, scale only gaps.
        """

        # If not fitting to the area, do nothing.
        if not self.is_fit:
            return

        # Calculate the width/height of the bounding area
        top_left, top_right, bottom_right, bottom_left = [np.array(coord) for coord in self.area_corners]
        area_width_m = self.haversine_distance(top_left, top_right)
        area_height_m = self.haversine_distance(top_left, bottom_left)

        # Calculate total space needed for (parcel + gap) in x & y directions
        total_parcel_width = (
            self.num_parcels_x * (self.parcel_width_m + self.gap_x_m)
            - (self.gap_x_m if self.gap_x_m != 0 else 0)
        )
        total_parcel_height = (
            self.num_parcels_y * (self.parcel_height_m + self.gap_y_m)
            - (self.gap_y_m if self.gap_y_m != 0 else 0)
        )

        # If these are 0 or extremely small, avoid division by zero
        if abs(total_parcel_width) < 1e-12:
            total_parcel_width = 1e-12
        if abs(total_parcel_height) < 1e-12:
            total_parcel_height = 1e-12

        if self.preserve_parcel_size:
            # Only scale the gap to fit
            scale_x = area_width_m / total_parcel_width
            scale_y = area_height_m / total_parcel_height

            # This factor ensures the entire arrangement fits
            scale_factor = min(scale_x, scale_y)
            
            # Apply scaling only to the gaps
            if abs(self.gap_x_m) > 1e-12:
                self.gap_x_m *= scale_factor
            if abs(self.gap_y_m) > 1e-12:
                self.gap_y_m *= scale_factor

        else:
            # Scale parcels and gaps together
            scale_x = area_width_m / total_parcel_width
            scale_y = area_height_m / total_parcel_height
            scale_factor = min(scale_x, scale_y)

            # Scale parcel dimensions
            self.parcel_width_m *= scale_factor
            self.parcel_height_m *= scale_factor
            
            # Scale gap if non-zero
            if abs(self.gap_x_m) > 1e-12:
                self.gap_x_m *= scale_factor
            if abs(self.gap_y_m) > 1e-12:
                self.gap_y_m *= scale_factor

        # If gaps were initially zero (or extremely close to zero), ensure they stay zero
        if abs(self.gap_x_m) < 1e-12:
            self.gap_x_m = 0.0
        if abs(self.gap_y_m) < 1e-12:
            self.gap_y_m = 0.0

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

        lat2 = math.asin(
            math.sin(lat1) * math.cos(distance / R) +
            math.cos(lat1) * math.sin(distance / R) * math.cos(bearing)
        )
        lon2 = lon1 + math.atan2(
            math.sin(bearing) * math.sin(distance / R) * math.cos(lat1),
            math.cos(distance / R) - math.sin(lat1) * math.sin(lat2)
        )

        return math.degrees(lat2), math.degrees(lon2)

    def generate_parcel_coordinates(self):
        """
        Main method to generate parcel polygons (4-corner coordinates + color).
        Call after the instance is created (and possibly fitted) to get final results.
        """
        # Get the corner coordinates
        top_left, top_right, bottom_right, bottom_left = [np.array(coord) for coord in self.area_corners]

        # Calculate bearings for the top and left edges
        bearing_x = math.atan2(top_right[1] - top_left[1], top_right[0] - top_left[0])
        bearing_y = math.atan2(bottom_left[1] - top_left[1], bottom_left[0] - top_left[0])

        # List to store the parcel coordinates
        parcels = []
        for j in range(self.num_parcels_y):
            for i in range(self.num_parcels_x):
                # Move to the origin of the current parcel (distance along top edge, then down along left edge)
                move_x = i * (self.parcel_width_m + self.gap_x_m)
                move_y = j * (self.parcel_height_m + self.gap_y_m)

                # Move horizontally (top edge direction), then vertically (left edge direction)
                parcel_origin_lat, parcel_origin_lng = self.move_point(top_left[0], top_left[1], move_x, bearing_x)
                parcel_origin_lat, parcel_origin_lng = self.move_point(parcel_origin_lat, parcel_origin_lng, move_y, bearing_y)

                # Calculate the corners of the parcel
                parcel_top_left = (parcel_origin_lat, parcel_origin_lng)
                parcel_top_right = self.move_point(parcel_origin_lat, parcel_origin_lng, self.parcel_width_m, bearing_x)
                parcel_bottom_right = self.move_point(
                    parcel_top_right[0], parcel_top_right[1], self.parcel_height_m, bearing_y
                )
                parcel_bottom_left = self.move_point(
                    parcel_origin_lat, parcel_origin_lng, self.parcel_height_m, bearing_y
                )

                # Assign color in a cycle through the colors list
                color = self.colors[(j * self.num_parcels_x + i) % len(self.colors)]

                # Store the parcel data
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
