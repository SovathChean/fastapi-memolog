"""Base service class."""

from abc import ABC

from app.common.logging import get_logger


class BaseService(ABC):
    """Base class for all services.

    Provides common functionality like logging.
    """

    def __init__(self):
        """Initialize base service with logger."""
        self.logger = get_logger(self.__class__.__name__)
