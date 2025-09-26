from workers.example_worker import handle_email_attachment


def test_ok():
    assert handle_email_attachment(b"pdf")["ok"] is True
