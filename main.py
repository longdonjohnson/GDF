import os
import threading
import numpy as np
import cv2

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.properties import StringProperty, ObjectProperty, NumericProperty
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.uix.button import Button
from kivy.utils import platform

# Import engine
from gdf_engine import ImageProcessor, PRESETS

class ImageWidget(Widget):
    source_image = StringProperty('')

class MainLayout(BoxLayout):
    status_message = StringProperty('Ready')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.processor = ImageProcessor()
        self.current_display_texture = None

        # Populate presets
        self.populate_presets()

    def populate_presets(self):
        container = self.ids.preset_container
        for name in PRESETS.keys():
            btn = Button(text=name, size_hint=(None, 1), width=150)
            btn.bind(on_release=lambda x, n=name: self.trigger_preset(n))
            container.add_widget(btn)

    def show_load_dialog(self):
        if platform == 'android':
            from android.permissions import request_permissions, Permission
            from plyer import filechooser

            def callback(permissions, results):
                if all(results):
                    filechooser.open_file(on_selection=self.load_image_callback)
                else:
                    self.status_message = "Permissions denied"

            request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE], callback)
        else:
            # Desktop fallback (mocking or simple input)
            # For simplicity in testing, let's assume a hardcoded path or simple input if not android
            # But normally we'd use plyer's filechooser which works on desktop too
            try:
                from plyer import filechooser
                filechooser.open_file(on_selection=self.load_image_callback)
            except Exception as e:
                print(f"Filechooser error: {e}")
                self.status_message = "Filechooser not available"

    def load_image_callback(self, selection):
        if not selection:
            return

        filepath = selection[0]
        self.status_message = f"Loading {os.path.basename(filepath)}..."

        # Load in thread
        threading.Thread(target=self._load_image_thread, args=(filepath,)).start()

    def _load_image_thread(self, filepath):
        try:
            self.processor.load_image(filepath)
            Clock.schedule_once(lambda dt: self._post_load_success())
        except Exception as e:
            Clock.schedule_once(lambda dt: self._post_load_failure(str(e)))

    def _post_load_success(self):
        self.status_message = "Image Loaded"
        self.ids.truth_fader.value = 0.0 # Reset to Raw
        self.update_display()

    def _post_load_failure(self, error):
        self.status_message = f"Error: {error}"

    def trigger_preset(self, name):
        if self.processor.original_layer is None:
            self.status_message = "Load an image first"
            return

        self.status_message = f"Applying {name}..."
        threading.Thread(target=self._apply_preset_thread, args=(name,)).start()

    def _apply_preset_thread(self, name):
        self.processor.apply_preset(name)
        Clock.schedule_once(lambda dt: self._post_preset_success(name))

    def _post_preset_success(self, name):
        self.status_message = f"Applied {name}"
        self.ids.truth_fader.value = 1.0 # Auto-fade to processed
        self.update_display()

    def on_slider_change(self, value):
        if self.processor.original_layer is not None:
            self.update_display(alpha=value)

    def update_display(self, alpha=None):
        if alpha is None:
            alpha = self.ids.truth_fader.value

        if self.processor.original_layer is None:
            return

        # Blend
        # original is A, processed is B
        # result = (1-alpha)*A + alpha*B

        # Ensure processed layer exists (it is initialized to original copy)
        # But if we just loaded, it might be same.

        # We need to do this efficiently.
        # cv2.addWeighted expects compatible arrays.

        img_a = self.processor.original_layer
        img_b = self.processor.processed_layer

        # Blend
        blended = cv2.addWeighted(img_a, 1.0 - alpha, img_b, alpha, 0.0)

        # Convert to texture
        self._update_texture(blended)

    def _update_texture(self, img_float):
        # Convert float32 (0-1) to uint8 (0-255) for display
        img_uint8 = (np.clip(img_float, 0, 1) * 255).astype(np.uint8)

        # Flip for Kivy (Kivy texture is bottom-up)
        img_uint8 = cv2.flip(img_uint8, 0)

        # Create texture
        # Assuming RGB
        buf = img_uint8.tobytes()
        texture = Texture.create(size=(img_uint8.shape[1], img_uint8.shape[0]), colorfmt='rgb')
        texture.blit_buffer(buf, colorfmt='rgb', bufferfmt='ubyte')

        self.ids.image_widget.ids.main_image.texture = texture


class GDFApp(App):
    def build(self):
        return MainLayout()

if __name__ == '__main__':
    GDFApp().run()
