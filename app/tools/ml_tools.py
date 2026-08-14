import joblib
import numpy as np

class MLTools:
    def __init__(self, ocsvm_path=None, reg_path=None):
        self.ocsvm = joblib.load(ocsvm_path) if ocsvm_path else None
        self.reg = joblib.load(reg_path) if reg_path else None

    def detect_anomalies(self, X):
        preds = self.ocsvm.predict(X)
        return preds  # -1 anomaly, 1 normal

    def predict(self, X):
        return self.reg.predict(X)
