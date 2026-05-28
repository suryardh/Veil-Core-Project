import json
import os
import tempfile

from utils.logger import log

class JSONStore:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.data = {}
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                log.warning("Load error from %s: %s", self.filepath, e)
                self.data = {}
        else:
            self.data = {}
            self._save()

    def _save(self):
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=os.path.dirname(self.filepath),
                prefix=".tmp_", suffix=".json", delete=False
            ) as tmp:
                json.dump(self.data, tmp, indent=4, ensure_ascii=False)
                tmp_path = tmp.name
            os.replace(tmp_path, self.filepath)
        except Exception as e:
            log.warning("Save error to %s: %s", self.filepath, e)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value, autosave=True):
        self.data[key] = value
        if autosave:
            self._save()

    def delete(self, key, autosave=True):
        if key in self.data:
            del self.data[key]
            if autosave:
                self._save()

    def clear(self, autosave=True):
        self.data = {}
        if autosave:
            self._save()
