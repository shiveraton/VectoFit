"""Quantifying differences in movement between the left and right sides of the body."""

# calculate the percentage difference between two corresponding measurements from the left and right sides
def calculate_asymmetry(left_angle, right_angle):
    difference = abs(left_angle - right_angle)
    average = (left_angle + right_angle) / 2

    if average == 0:
        return None
    
    percentage = difference / average * 100

    return percentage

def calculate_asymmetry_series(left_angles, right_angles):
    asymmetries = []

    if len(left_angles) != len(right_angles):
        raise ValueError("left_angles and right_angles must have the same length")

    for (left_angle, right_angle) in (zip(left_angles, right_angles)):
        asymmetry = calculate_asymmetry(left_angle, right_angle)
        asymmetries.append(asymmetry)

    return asymmetries