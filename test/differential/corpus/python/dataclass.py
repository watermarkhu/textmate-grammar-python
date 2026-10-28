from dataclasses import dataclass


@dataclass(frozen=True)
class Point:
    x: float
    y: float = 0.0

    def distance(self, other: "Point") -> float:
        """Return the Euclidean distance from this point."""
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5
