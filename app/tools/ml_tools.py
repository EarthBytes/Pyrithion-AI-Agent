from pathlib import Path

import joblib
import numpy as np

class MLTools:
    def __init__(self, ocsvm_path=None, reg_path=None):
        self.ocsvm = self._load_model(ocsvm_path)
        self.reg = self._load_model(reg_path)

    @staticmethod
    def _load_model(path):
        if path and Path(path).exists():
            return joblib.load(path)
        return None

    def detect_anomalies(self, X):
        X = np.asarray(X).reshape(-1, 1)
        if self.ocsvm is None:
            mean = X.mean()
            std = X.std() or 1.0
            z_scores = np.abs((X - mean) / std)
            return np.where(z_scores > 2.0, -1, 1).flatten()
        return self.ocsvm.predict(X)

    def predict(self, X):
        if self.reg is None:
            X = np.asarray(X).reshape(-1, 1)
            return np.full(X.shape[0], X.mean())
        return self.reg.predict(X)
