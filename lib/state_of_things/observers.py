try:
    from typing import List
except ImportError:  # pragma: no cover
    pass


class Observers:
    """
    Maintain a list of observers that will be notified when an event
    occurs.
    """

    def __init__(self) -> None:
        self._observers: List = []

    def attach(self, observer: object):
        """
        Attach an observer that will be notified of events that it
        supports.

        Args:
            observer (object): the observer to attach.
        """
        self._observers.append(observer)

    def detach(self, observer: object):
        """
        Detach an observer so that it will no longer be notified when
        events occur.

        Args:
            observer (object): the observer to detach.
        """
        self._observers.remove(observer)

    def notify(self, event_name: str, *params: object):
        """
        Notify all observers that an event has occurred. Each attached
        observer with a defined function that matches the event name
        will called with the passed in event's params.

        Args:
            event_name (str): event that has occurred.
            params (*object): optional event data
        """
        for observer in self._observers:
            handler = getattr(observer, event_name, None)
            if callable(handler):
                handler(*params)
