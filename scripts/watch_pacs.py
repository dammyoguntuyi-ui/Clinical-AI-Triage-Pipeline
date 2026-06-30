import time
import os
import subprocess
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

WATCH_DIR = os.path.abspath("./test_images")

class DicomBatchHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.timer = None
        self.lock = threading.Lock()

    def process_event(self, event):
        # Natively screen for DICOM extensions
        if not event.is_directory and event.src_path.lower().endswith('.dcm'):
            with self.lock:
                # If a countdown timer is already running, cancel it!
                if self.timer is not None:
                    self.timer.cancel()
                
                # Start a fresh 5-second countdown window
                # This accumulates all rapid-fire patient modifications into a single event block
                self.timer = threading.Timer(5.0, self.execute_pipeline, args=[event.src_path])
                self.timer.start()

    def execute_pipeline(self, sample_filepath):
        print(f"\n🚀 [BATCH EVENT TRIGGER] Ingestion quiet window achieved.")
        print(f"📦 Processing complete batch starting from: {os.path.basename(sample_filepath)}")
        print("⚡ Executing automated data orchestration engine...")
        
        try:
            # Execute your clinical triage report compilation script exactly once
            subprocess.run(["python", "scripts/ai_csv_generator.py"], check=True)
            print("✅ Automated processing chain completed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"❌ Automation Error during script execution: {e}")

    def on_created(self, event):
        self.process_event(event)

    def on_modified(self, event):
        self.process_event(event)

if __name__ == "__main__":
    if not os.path.exists(WATCH_DIR):
        os.makedirs(WATCH_DIR)
        
    event_handler = DicomBatchHandler()
    observer = Observer()
    observer.schedule(event_handler, path=WATCH_DIR, recursive=False)
    
    print(f"🕵️‍♂️ [STATUS] Active Event Listener listening on: {WATCH_DIR}")
    print("📥 Waiting for new clinical data drops... Press Ctrl+C to stop.")
    
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Event listener shutting down safely.")
        observer.stop()
    observer.join()