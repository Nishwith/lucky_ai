from enum import Enum
from backend.core.logger import logger

class SystemState(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    READY = "READY"
    THINKING = "THINKING"
    EXECUTING = "EXECUTING"
    SPEAKING = "SPEAKING"
    ERROR = "ERROR"

class SystemStateMachine:
    def __init__(self):
        # We start in CONNECTING state until validation resolves
        self._current_state = SystemState.CONNECTING
        logger.info(f"System State Machine initialized. Initial state: {self._current_state}")

    @property
    def current_state(self) -> SystemState:
        return self._current_state

    def transition_to(self, new_state: SystemState, reason: str = ""):
        if new_state == self._current_state:
            return
        
        old_state = self._current_state
        self._current_state = new_state
        log_msg = f"System state transition: {old_state} -> {new_state}"
        if reason:
            log_msg += f" (Reason: {reason})"
        logger.info(log_msg)

# Global singleton system state machine
system_state = SystemStateMachine()
