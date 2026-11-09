"""Pure decision logic. Port of AutoOffPolicy.swift and LidSessionTracker.swift."""

NONE, SUSPEND, RESUME = "none", "suspend", "resume"


def decide(intent, suspended, percent, on_ac, threshold, overridden=False, hysteresis=5):
    if threshold <= 0:
        return NONE
    if not suspended and intent and not on_ac and not overridden and percent < threshold:
        return SUSPEND
    if suspended and on_ac and percent >= threshold + hysteresis:
        return RESUME
    return NONE


def should_keep_override(overridden, on_ac):
    return overridden and not on_ac


class LidSessionTracker:
    INACTIVE, WAITING_FOR_CLOSE, WAITING_FOR_OPEN = range(3)

    def __init__(self):
        self.state = self.INACTIVE

    @property
    def is_active(self):
        return self.state != self.INACTIVE

    @property
    def is_waiting_for_close(self):
        return self.state == self.WAITING_FOR_CLOSE

    def start(self, lid_closed):
        self.state = self.WAITING_FOR_OPEN if lid_closed is True else self.WAITING_FOR_CLOSE

    def cancel(self):
        self.state = self.INACTIVE

    def handle(self, lid_closed):
        """True exactly once: when a started session sees the lid reopen after a close."""
        if self.state == self.WAITING_FOR_CLOSE and lid_closed:
            self.state = self.WAITING_FOR_OPEN
        elif self.state == self.WAITING_FOR_OPEN and not lid_closed:
            self.state = self.INACTIVE
            return True
        return False
