import threading
import time

from macagentic.agent.environment import InterruptibleLocalEnvironment


def test_interrupt_terminates_running_command() -> None:
    environment = InterruptibleLocalEnvironment(timeout=30)
    results = []
    execution = threading.Thread(
        target=lambda: results.append(
            environment.execute({"command": "sleep 30"})
        )
    )
    execution.start()

    deadline = time.monotonic() + 1
    while not environment._processes and time.monotonic() < deadline:
        time.sleep(0.01)

    environment.interrupt()
    execution.join(1)

    assert not execution.is_alive()
    assert results[0]["returncode"] != 0
