from macagentic.agent.transcript import Transcript


def test_transcript_keeps_text_in_memory_and_notifies() -> None:
    notifications = []
    transcript = Transcript(on_change=lambda: notifications.append(True))

    transcript.write("first")
    transcript.write(" second")

    assert transcript.getvalue() == "first second"
    assert len(notifications) == 2
