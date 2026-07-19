"""Module entrypoint for `python -m pm_agent.dashboard`."""

from pm_agent.dashboard.server import serve


if __name__ == "__main__":
    serve()
