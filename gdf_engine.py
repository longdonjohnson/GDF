import cv2
import numpy as np

class ImageProcessor:
    def __init__(self):
        self.original_layer = None
        self.processed_layer = None
        self.current_preset = None

    def load_image(self, path):
        """
        Loads an image from path and converts it to float32 [0.0, 1.0].
        Initializes original_layer and processed_layer.
        """
        # Load image in color
        img = cv2.imread(path)
        if img is None:
            raise ValueError(f"Could not load image from {path}")

        # Convert BGR to RGB (OpenCV loads as BGR)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Convert to float32 and normalize to 0-1
        img_float = img.astype(np.float32) / 255.0

        self.original_layer = img_float
        # Initialize processed layer as a copy of original
        self.processed_layer = img_float.copy()

        return True

    def module_log_stretch(self, image, strength=10.0):
        """
        Applies logarithmic stretch to the image.
        strength: Controls the steepness of the curve.
        """
        # Avoid log(0)
        c = strength
        # Formula: output = c * log(1 + input) / log(1 + c)
        # But commonly: output = log(1 + strength * input) / log(1 + strength)
        # Let's use a standard normalization approach

        # Ensure we don't have negative values
        image_safe = np.maximum(image, 0.0)

        mapped = np.log1p(strength * image_safe) / np.log1p(strength)
        return np.clip(mapped, 0.0, 1.0).astype(np.float32)

    def module_clahe(self, image, clip_limit=2.0, tile_grid_size=(8, 8)):
        """
        Applies Contrast Limited Adaptive Histogram Equalization.
        Note: CLAHE works on luminance channel usually.
        """
        # Convert to LAB to apply CLAHE on L channel
        # image is float32 RGB 0-1.
        # cv2.cvtColor expects float32 to be 0-1.

        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)

        # CLAHE in OpenCV requires uint8 or uint16 usually?
        # Let's check docs. createCLAHE apply takes numpy array.
        # For float images, we usually need to convert to uint8 for standard CLAHE implementation
        # or implement a float version. OpenCV CLAHE primarily supports 8-bit and 16-bit.

        # Conversion to uint8 for CLAHE processing
        l_uint8 = (l * 255.0).astype(np.uint8)

        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
        cl_uint8 = clahe.apply(l_uint8)

        # Convert back to float
        cl = cl_uint8.astype(np.float32) / 255.0

        # Merge
        lab_merged = cv2.merge((cl, a, b))
        result = cv2.cvtColor(lab_merged, cv2.COLOR_LAB2RGB)

        return np.clip(result, 0.0, 1.0)

    def module_high_pass(self, image, kernel_size=21):
        """
        Applies High Pass filter: Gaussian Blur, Invert, Blend.
        Returns a gray-centered high pass image (details).
        """
        if kernel_size % 2 == 0:
            kernel_size += 1

        # 1. Gaussian Blur
        blurred = cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)

        # 2. Invert the blurred image (1 - blur)
        inverted_blur = 1.0 - blurred

        # 3. Blend: 50% Original + 50% Inverted Blur
        # This results in 0.5 + 0.5 * (Original - Blur)
        # Gray is 0.5.
        high_pass = 0.5 * image + 0.5 * inverted_blur

        return np.clip(high_pass, 0.0, 1.0)

    def apply_preset(self, name):
        """
        Applies a named preset to the original layer and updates processed_layer.
        """
        if self.original_layer is None:
            return

        temp_image = self.original_layer.copy()

        # Define Presets Configuration
        # VOID_HUNTER: Emphasize low light details (Log Stretch + Strong CLAHE)
        # HULL_SCANNER: Edge detection / Structure (High Pass)
        # WAKE_MAPPER: Flow visualization (Maybe Blur + CLAHE or just Moderate CLAHE + Log)

        if name == 'VOID_HUNTER':
            # Dig into the darks
            temp_image = self.module_log_stretch(temp_image, strength=50.0)
            temp_image = self.module_clahe(temp_image, clip_limit=4.0)

        elif name == 'HULL_SCANNER':
            # Surface details
            # Maybe a slight contrast boost first
            temp_image = self.module_clahe(temp_image, clip_limit=2.0)
            temp_image = self.module_high_pass(temp_image, kernel_size=31)
            # Maybe stretch the contrast of the high pass result?
            # Let's keep it simple as requested.

        elif name == 'WAKE_MAPPER':
            # Mapping density/wakes
            temp_image = self.module_log_stretch(temp_image, strength=10.0)
            # High pass with larger kernel for "wakes"
            temp_image = self.module_high_pass(temp_image, kernel_size=51)
            # Add some contrast back
            temp_image = self.module_clahe(temp_image, clip_limit=3.0)

        else:
            print(f"Unknown preset: {name}")

        self.processed_layer = temp_image
        self.current_preset = name

        return self.processed_layer

PRESETS = {
    'VOID_HUNTER': 'Deep space object analysis',
    'HULL_SCANNER': 'Structural anomaly detection',
    'WAKE_MAPPER': 'Propulsion trail visualization'
}
