# ... same imports ...

# Persistent storage
DATA_DIR = "/data"
os.makedirs(DATA_DIR, exist_ok=True)
SEEN_FILE = f"{DATA_DIR}/seen_images.pkl"

def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "rb") as f:
                data = pickle.load(f)
                # Force it to be a set
                return set(data) if isinstance(data, (list, dict, set)) else set()
        except:
            pass
    return set()

def save_seen(seen):
    try:
        with open(SEEN_FILE, "wb") as f:
            pickle.dump(list(seen), f)  # Save as list → always reloads as set
    except:
        pass

seen_images = load_seen()
all_files = []

# ... rest of your code unchanged ...