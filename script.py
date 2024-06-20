import os
import time
import threading
from queue import Queue
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class Watcher:
    def __init__(self, directory_to_watch):
        self.DIRECTORY_TO_WATCH = directory_to_watch
        self.observer = Observer()
        self.queue = Queue()
        self.ensure_initial_file()
        
    def ensure_initial_file(self):
        if not os.listdir(self.DIRECTORY_TO_WATCH):
            print("Directory is empty at startup. Creating a new log file.")
            self.create_new_log_file(self.DIRECTORY_TO_WATCH)

    def create_new_log_file(self, folder_path):
        new_file_name = f"{int(time.time())}.log"
        new_file_path = os.path.join(folder_path, new_file_name)
        with open(new_file_path, 'w') as new_file:
            new_file.write("New log file created.")
        print(f"[{self.get_current_timestamp()}] Created new file: {new_file_name}")

    def get_current_timestamp(self):
        return time.strftime('%Y-%m-%d %H:%M:%S')

    def handle_file_operation(self):
        while True:
            operation, file_path = self.queue.get()
            if operation == 'create':
                self.create_new_log_file(file_path)
            elif operation == 'delete':
                self.delete_file(file_path)
            self.queue.task_done()

    def run(self):
        print('Watching %s...' % self.DIRECTORY_TO_WATCH)
        event_handler = Handler(self.DIRECTORY_TO_WATCH, self.queue)
        self.observer.schedule(event_handler, self.DIRECTORY_TO_WATCH, recursive=False)
        self.observer.start()

        # Start the thread to handle file operations
        threading.Thread(target=self.handle_file_operation, daemon=True).start()

        try:
            while True:
                # Check file size and create new file if necessary
                self.check_files()
                time.sleep(3)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()

    def check_files(self):
        folder_path = self.DIRECTORY_TO_WATCH
        files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
        files = sorted(files, key=lambda f: os.path.getctime(os.path.join(folder_path, f)))

        if len(files) > 0 and os.path.getsize(os.path.join(folder_path, files[-1])) >= 1 * 1024:  # 1KB
            self.create_new_log_file(folder_path)

        # Check if more than 3 files exist, delete the oldest one
        if len(files) > 3:
            oldest_file = os.path.join(folder_path, files[0])
            self.queue.put(('delete', oldest_file))

    def delete_file(self, file_path):
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"[{self.get_current_timestamp()}] Deleted file: {os.path.basename(file_path)}")
        else:
            print(f"[{self.get_current_timestamp()}] File not found: {os.path.basename(file_path)}")

class Handler(FileSystemEventHandler):
    def __init__(self, directory, queue):
        self.directory = directory
        self.queue = queue

    def on_any_event(self, event):
        if event.is_directory:
            return None
        elif event.event_type == 'created':
            file_path = os.path.join(self.directory, event.src_path)
            if os.path.isfile(file_path):
                self.queue.put(('create', file_path))
        elif event.event_type == 'deleted':
            file_path = os.path.join(self.directory, event.src_path)
            if os.path.isfile(file_path):
                self.queue.put(('delete', file_path))

if __name__ == '__main__':
    path_to_watch = "./watched_folder"  # Specify the folder you want to watch
    if not os.path.exists(path_to_watch):
        os.makedirs(path_to_watch)
    
    watcher = Watcher(path_to_watch)
    watcher.run()
