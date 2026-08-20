from app.email.attachments import build_report_attachments, build_report_text


def test_build_report_text_includes_question_and_answer():
    text = build_report_text(
        goal="What is the marketing budget?",
        report_body="The marketing budget is £6000.",
        sources=[{"filename": "budget.csv", "score": 0.91}],
        brand_name="Pyrithion AI",
    )
    assert "What is the marketing budget?" in text
    assert "£6000" in text
    assert "budget.csv" in text


def test_build_report_attachments_returns_txt_and_docx():
    attachments = build_report_attachments(
        task_id="task-123",
        goal="Summarise Q3 policy",
        report_body="Policy summary here.",
        sources=[],
        brand_name="Pyrithion AI",
    )
    assert len(attachments) == 2
    names = [name for name, _, _ in attachments]
    assert names[0].endswith(".txt")
    assert names[1].endswith(".docx")
    txt_bytes = attachments[0][1]
    assert b"Policy summary here." in txt_bytes
    assert attachments[1][1][:2] == b"PK"
