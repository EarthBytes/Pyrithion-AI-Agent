import numpy as np

from app.tools.filesystem import FilesystemTool
from app.tools.ml_tools import MLTools
from app.tools.rag import RAGTool
from app.utils.id_generator import generate_task_id


def test_generate_task_id_unique():
    ids = {generate_task_id() for _ in range(10)}
    assert len(ids) == 10


def test_filesystem_tool_save_and_read(filesystem_tool):
    path = filesystem_tool.save_report("abc123", "report content")
    assert path.exists()
    assert filesystem_tool.read_report("abc123") == "report content"
    assert "abc123" in filesystem_tool.list_reports()


def test_ml_tools_fallback_anomaly_detection():
    ml = MLTools()
    values = np.array([10, 11, 10, 9, 10, 50]).reshape(-1, 1)
    preds = ml.detect_anomalies(values)
    assert -1 in preds


def test_ml_tools_fallback_predict():
    ml = MLTools()
    values = np.array([10, 20, 30]).reshape(-1, 1)
    preds = ml.predict(values)
    assert len(preds) == 3


def test_rag_default_embed_is_deterministic():
    rag = RAGTool()
    v1 = rag.embed_fn("energy usage")
    v2 = rag.embed_fn("energy usage")
    assert v1 == v2
    assert len(v1) == 384
