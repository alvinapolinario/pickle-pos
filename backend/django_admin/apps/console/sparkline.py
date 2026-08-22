"""SVG sparkline helper for KPI cards."""


def sparkline_points(values: list[int] | list[float], width: int = 88, height: int = 28) -> str:
    if not values:
        return ""
    min_v = min(values)
    max_v = max(values)
    span = max(max_v - min_v, 1)
    step = width / max(len(values) - 1, 1)
    points = []
    for index, value in enumerate(values):
        x = round(index * step, 2)
        y = round(height - ((value - min_v) / span) * (height - 2) - 1, 2)
        points.append(f"{x},{y}")
    return " ".join(points)
