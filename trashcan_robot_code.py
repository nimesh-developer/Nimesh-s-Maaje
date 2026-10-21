import cv2
import numpy as np
import time
import math
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    print("RPi.GPIO not found. Running in simulation/test mode.")
    GPIO_AVAILABLE = False

# --- Hardware Configuration (Mecanum setup for omnidirectional movement without turning) ---
# Assuming 4 DC motors connected to 2 L298N drivers
# Pins (Mock examples, adjust based on actual wiring)
MOTOR_FL_IN1 = 17
MOTOR_FL_IN2 = 27
MOTOR_FR_IN1 = 22
MOTOR_FR_IN2 = 23
MOTOR_BL_IN1 = 24
MOTOR_BL_IN2 = 25
MOTOR_BR_IN1 = 5
MOTOR_BR_IN2 = 6

def setup_gpio():
    if not GPIO_AVAILABLE:
        return
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    pins = [MOTOR_FL_IN1, MOTOR_FL_IN2, MOTOR_FR_IN1, MOTOR_FR_IN2,
            MOTOR_BL_IN1, MOTOR_BL_IN2, MOTOR_BR_IN1, MOTOR_BR_IN2]
    for pin in pins:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)

def stop_motors():
    if not GPIO_AVAILABLE:
        print("MOCK: Stop motors")
        return
    pins = [MOTOR_FL_IN1, MOTOR_FL_IN2, MOTOR_FR_IN1, MOTOR_FR_IN2,
            MOTOR_BL_IN1, MOTOR_BL_IN2, MOTOR_BR_IN1, MOTOR_BR_IN2]
    for pin in pins:
        GPIO.output(pin, GPIO.LOW)

def move_robot(x_speed, y_speed):
    """
    Simplified Mecanum kinematic control.
    x_speed: lateral speed (-1 to 1)
    y_speed: forward/backward speed (-1 to 1)
    We omit rotation speed to prevent tipping by sudden turns.
    """
    if not GPIO_AVAILABLE:
        # print(f"MOCK: Move Robot - X: {x_speed:.2f}, Y: {y_speed:.2f}")
        return

    # In a real scenario with PWM, we'd calculate speeds.
    # Here we just do basic directional logic for simplicity.
    if y_speed > 0: # Forward
        GPIO.output(MOTOR_FL_IN1, GPIO.HIGH)
        GPIO.output(MOTOR_FR_IN1, GPIO.HIGH)
        GPIO.output(MOTOR_BL_IN1, GPIO.HIGH)
        GPIO.output(MOTOR_BR_IN1, GPIO.HIGH)
    elif y_speed < 0: # Backward
        GPIO.output(MOTOR_FL_IN2, GPIO.HIGH)
        GPIO.output(MOTOR_FR_IN2, GPIO.HIGH)
        GPIO.output(MOTOR_BL_IN2, GPIO.HIGH)
        GPIO.output(MOTOR_BR_IN2, GPIO.HIGH)
    elif x_speed > 0: # Right (strafe)
        GPIO.output(MOTOR_FL_IN1, GPIO.HIGH)
        GPIO.output(MOTOR_FR_IN2, GPIO.HIGH)
        GPIO.output(MOTOR_BL_IN2, GPIO.HIGH)
        GPIO.output(MOTOR_BR_IN1, GPIO.HIGH)
    elif x_speed < 0: # Left (strafe)
        GPIO.output(MOTOR_FL_IN2, GPIO.HIGH)
        GPIO.output(MOTOR_FR_IN1, GPIO.HIGH)
        GPIO.output(MOTOR_BL_IN1, GPIO.HIGH)
        GPIO.output(MOTOR_BR_IN2, GPIO.HIGH)
    else:
        stop_motors()

    # We would need PWM for actual proportional speed control
    time.sleep(0.1) # Short pulse
    stop_motors()

def predict_landing(trajectory_points):
    """Predicts landing X coordinate based on trajectory"""
    if len(trajectory_points) < 5:
        return None
    x_coords = np.array([p[0] for p in trajectory_points])
    y_coords = np.array([p[1] for p in trajectory_points])
    try:
        coeffs = np.polyfit(x_coords, y_coords, 2)
        landing_y = 480 # Bottom of a 640x480 frame
        roots = np.roots([coeffs[0], coeffs[1], coeffs[2] - landing_y])
        valid_roots = [r for r in roots if np.isreal(r) and ((x_coords[-1] > x_coords[0] and r > x_coords[-1]) or (x_coords[-1] < x_coords[0] and r < x_coords[-1]))]
        if valid_roots:
            return int(np.real(valid_roots[0]))
    except:
        pass
    return None

def main():
    print("Initializing Real-Time Trashcan Robot...")
    setup_gpio()

    # Try opening Pi Camera or USB webcam
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Camera not found. Please ensure it's connected.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # For auto-tracking, we might use color detection (e.g., bright orange ball)
    # instead of manual ROI selection since the robot is autonomous.

    # We'll use a simple background subtractor to detect a thrown object
    fgbg = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=50, detectShadows=False)

    trajectory = []
    tracking = False

    print("Robot ready. Waiting for object...")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Basic motion detection
            fgmask = fgbg.apply(frame)
            contours, _ = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            largest_contour = None
            max_area = 0
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if 500 < area < 10000: # Filter noise and huge changes
                    if area > max_area:
                        max_area = area
                        largest_contour = cnt

            if largest_contour is not None:
                (x, y, w, h) = cv2.boundingRect(largest_contour)
                center_x = x + w//2
                center_y = y + h//2

                # Only track if it's high up (being thrown)
                if center_y < 240 or tracking:
                    tracking = True
                    trajectory.append((center_x, center_y))
                    cv2.circle(frame, (center_x, center_y), 5, (0, 255, 0), -1)

                    if len(trajectory) > 20:
                        trajectory.pop(0)

                    predicted_x = predict_landing(trajectory)

                    if predicted_x:
                        # Draw prediction
                        cv2.circle(frame, (predicted_x, 480), 20, (0, 0, 255), -1)

                        # --- Robot Control Logic ---
                        # Frame center is 320. We want the predicted_x to be at 320.
                        error = predicted_x - 320

                        # Simple proportional control
                        if error > 50:
                            # Object landing to the right, move right
                            move_robot(1, 0)
                        elif error < -50:
                            # Object landing to the left, move left
                            move_robot(-1, 0)
                        else:
                            # It's going to land in the center, stay still or move forward slightly
                            # to ensure catching.
                            stop_motors()
            else:
                # Object lost or landed, reset
                if tracking:
                    stop_motors()
                tracking = False
                trajectory.clear()

            # For headless Pi, comment out imshow
            # cv2.imshow('Robot View', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        stop_motors()
        if GPIO_AVAILABLE:
            GPIO.cleanup()
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
