from .customer import Customer
from .appointment import Appointment
from .staff import Staff, STAFF_COLOR_PALETTE, suggest_next_color
from .service import Service

__all__ = ["Customer", "Appointment", "Staff", "Service",
           "STAFF_COLOR_PALETTE", "suggest_next_color"]
