from ..schemas import Mode

def plan(mode: Mode, prompt: str) -> Mode:
    # Start simple: honor user-selected mode; auto-route later
    return mode
