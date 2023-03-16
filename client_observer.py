from watchdog.observers import polling
from watchdog.events import PatternMatchingEventHandler


class FileEvent:
    def __init__(self, event_type, is_directory, src_path, dest_path=None):
        self.event_type = event_type.lower()
        self.is_directory = is_directory
        self.src_path = src_path
        self.dest_path = dest_path

    def __str__(self):
        rep = f"<FileEvent:" \
               f" event_type={self.event_type}," \
               f" is_directory={self.is_directory}" \
               f" src_path={self.src_path}>"
        if self.dest_path:
            rep = ', '.join([rep, self.dest_path])
        return rep


class ClientFileObserver:
    def __init__(self, root, on_any_event):
        patterns = ["*"]  # contains the file patterns we want to handle (in my scenario, I will handle all the files)
        ignore_patterns = None  # contains the patterns that we don’t want to handle.
        ignore_directories = False  # a boolean that we set to True if we want to be notified just for files.
        case_sensitive = False  # boolean that if set to “True”, made the patterns we introduced “case-sensitive”.

        # Create event handler:
        self._event_handler = PatternMatchingEventHandler(patterns, ignore_patterns, ignore_directories, case_sensitive)

        # Specify to the handler that we want this function to be called when an event is raised:
        self._event_handler.on_any_event = lambda event: on_any_event(event)
        self.root = root

        # Create an Observer:
        self._observer = polling.PollingObserver()  # better Observer

    def schedule(self):
        # 'recursive=True' allow me to catch events that occurs in subdirectories.
        self._observer.schedule(self._event_handler, self.root, recursive=True)

    def un_schedule(self):
        self._observer.unschedule_all()

    def start(self):
        self._observer.start()

    def stop(self):
        self._observer.stop()

    def join(self):
        self._observer.join()
