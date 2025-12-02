import cv2
import numpy as np
import os
import sys

# Add current directory to path so we can import gdf_engine
sys.path.append(os.getcwd())

from gdf_engine import ImageProcessor

def test_engine():
    print("Initializing ImageProcessor...")
    processor = ImageProcessor()

    # Check assets
    assets_dir = 'tests/assets'
    if not os.path.exists(assets_dir):
        print("tests/assets directory not found. Skipping image tests.")
        return

    images = [f for f in os.listdir(assets_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

    if not images:
        print("No images found in tests/assets")
        return

    test_image_path = os.path.join(assets_dir, images[0])
    print(f"Testing with image: {test_image_path}")

    # Test Load
    processor.load_image(test_image_path)
    print(f"Image loaded. Shape: {processor.original_layer.shape}, Dtype: {processor.original_layer.dtype}")
    assert processor.original_layer.dtype == np.float32
    assert processor.original_layer.max() <= 1.0

    # Test Presets
    presets = ['VOID_HUNTER', 'HULL_SCANNER', 'WAKE_MAPPER']

    for preset in presets:
        print(f"Applying preset: {preset}")
        result = processor.apply_preset(preset)
        print(f"Result stats: Mean={result.mean():.3f}, Max={result.max():.3f}, Min={result.min():.3f}")

        # Save output for visual verification
        output_filename = f"tests/output_{preset}.jpg"
        # Convert back to uint8 BGR for saving
        output_bgr = cv2.cvtColor(result, cv2.COLOR_RGB2BGR)
        output_uint8 = (output_bgr * 255.0).astype(np.uint8)
        cv2.imwrite(output_filename, output_uint8)
        print(f"Saved {output_filename}")

if __name__ == "__main__":
    test_engine()
