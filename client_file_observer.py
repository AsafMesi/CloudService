from watchdog.observers import polling
from watchdog.events import PatternMatchingEventHandler


class ClientFileObserver:
    def __init__(self, dir_path, syncer):
        patterns = ["*"]  # contains the file patterns we want to handle (in my scenario, I will handle all the files)
        ignore_patterns = None  # contains the patterns that we don’t want to handle.
        ignore_directories = False  # a boolean that we set to True if we want to be notified just for files.
        case_sensitive = False  # boolean that if set to “True”, made the patterns we introduced “case-sensitive”.

        # Create event handler:
        self._event_handler = PatternMatchingEventHandler(patterns, ignore_patterns, ignore_directories, case_sensitive)

        # specify to the handler that we want this function to be called when an event is raised:
        self._event_handler.on_any_event = lambda event: syncer.notify_server(event)
        self.dir_path = dir_path

        # create an Observer:
        self._observer = polling.PollingObserver()  # better Observer

    def schedule(self):
        go_recursively = True  # a boolean that allow me to catch all the event that occurs even in subdirectories.
        self._observer.schedule(self._event_handler, self.dir_path, recursive=go_recursively)

    def un_schedule(self):
        self._observer.unschedule_all()

    def start(self):
        self._observer.start()

    def stop(self):
        self._observer.stop()

    def join(self):
        self._observer.join()
