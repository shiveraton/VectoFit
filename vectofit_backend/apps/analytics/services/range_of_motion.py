def calculate_rom(angle_series) -> float:
    maximum_angle = max(angle_series)
    minimum_angle = min(angle_series)

    rom = maximum_angle - minimum_angle

    return rom

if __name__ == "__main__":
    print(calculate_rom([178, 165, 140, 110, 85, 110, 145, 170]))