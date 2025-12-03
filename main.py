from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.utils import platform

class GDFApp(App):
    def build(self):
        self.request_android_permissions()

        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        self.label = Label(text="GDF Mobile Tool")
        layout.add_widget(self.label)

        btn = Button(text="Load Image")
        btn.bind(on_release=self.load_file)
        layout.add_widget(btn)

        return layout

    def request_android_permissions(self):
        """
        Requests READ/WRITE_EXTERNAL_STORAGE permissions on Android.
        """
        if platform == 'android':
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE
            ])

    def load_file(self, instance):
        """
        Opens the file chooser using plyer.
        """
        try:
            from plyer import filechooser
            # Note: filechooser.open_file returns a selection, but acts asynchronously on some platforms
            # or requires a callback. Plyer's interface can vary.
            # Using standard open_file with on_selection callback.
            filechooser.open_file(on_selection=self.handle_selection)
        except Exception as e:
            self.label.text = f"Error: {e}"

    def handle_selection(self, selection):
        if selection:
            self.label.text = f"Selected: {selection[0]}"

if __name__ == '__main__':
    GDFApp().run()
