import math
import socket
import os
import time
from controller import Supervisor

supervisor = Supervisor()
joy = supervisor.getJoystick()
TIME_STEP = int(supervisor.getBasicTimeStep())

mot_left = supervisor.getDevice("left-wheel-motor")
mot_right = supervisor.getDevice("right-wheel-motor")
mot_left_enc = supervisor.getDevice("left-wheel-encoder")
mot_right_enc = supervisor.getDevice("right-wheel-encoder")
odo_left = supervisor.getDevice("left-odometry-encoder")
odo_right = supervisor.getDevice("right-odometry-encoder")
mot_left.setPosition(float('inf'))
mot_right.setPosition(float('inf'))
mot_left.setVelocity(0.0)
mot_right.setVelocity(0.0)
mot_left_enc.enable(TIME_STEP)
mot_right_enc.enable(TIME_STEP)
odo_left.enable(TIME_STEP)
odo_right.enable(TIME_STEP)

servo = supervisor.getDevice("servo")
vacuum = supervisor.getDevice("vacuum-gripper")
servo.setPosition(0)

camera = supervisor.getDevice("camera")
camera.enable(TIME_STEP)

# teleplot socket
addr = ("localhost", 47269)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_telemetry(name, value):
    now = time.time() * 1000
    msg = name+":"+str(now)+":"+str(value)
    sock.sendto(msg.encode(), addr)

def deg_to_rad(deg):
    return deg*math.pi/180.0

def mms_to_rads(mm):
    return mm/1000.0/MOTOR_WHEEL_RADIUS

def clip(val, min_, max_):
    if val < min_:
        return min_
    if val > max_:
        return max_
    return val

ODOMETRY_WHEEL_RADIUS = 0.024 # in m
MOTOR_WHEEL_RADIUS = 0.037 # in m
MAX_SPEED_ACCEL = mms_to_rads(4000.0) * (TIME_STEP/1000.0)  #in mm/s^-2
MAX_SPEED = 32 # in rad/s

def main():
    last_speed = 0
    servo_state = 0
    last_button_state = -1
    

    while supervisor.step(TIME_STEP) != -1:
        cmdtheta = 0
        cmdspeed = 0

        if not joy.isConnected():
            joy.enable(10)
        else:
            b = joy.getPressedButton()

            if b != last_button_state:
                if b == 0:
                    if vacuum.isOn():
                        vacuum.turnOff()
                    else:
                        vacuum.turnOn()

                if b == 5:
                    if servo_state == 0:
                        servo.setPosition(1.57)
                        servo_state = 1
                    else:
                        servo.setPosition(0)
                        servo_state = 0

            last_button_state = b

            a0 = joy.getAxisValue(0)
            a1 = joy.getAxisValue(1)
            a2 = joy.getAxisValue(2)
            a3 = joy.getAxisValue(3)
            a4 = joy.getAxisValue(4)
            a5 = joy.getAxisValue(5)
            # print(a0, a1, a2, a3, a4, a5)

            # idk why gamepad axes are different between my win10 and my linux
            # another quirk on my linux is until first press, a5 and a2 defaults to middle value 0.5
            if os.name == "posix":
                cmdtheta = a0/32767
                cmdspeed = (a5+32768)/65535 - (a2+32768)/65535
            else:
                cmdtheta = a1/32767
                cmdspeed = a5/32767 - a4/32767

        camera.getImage()

        theta = cmdtheta * deg_to_rad(300) * 2
        speed = cmdspeed * mms_to_rads(1000)

        if speed - last_speed > MAX_SPEED_ACCEL:
            speed = last_speed + MAX_SPEED_ACCEL
        if speed - last_speed < -MAX_SPEED_ACCEL:
            speed = last_speed - MAX_SPEED_ACCEL
        last_speed = speed

        right = -theta + speed
        left = theta + speed

        right = clip(right, -MAX_SPEED, MAX_SPEED)
        left = clip(left, -MAX_SPEED, MAX_SPEED)

        send_telemetry("right", right)
        send_telemetry("left", left)
        send_telemetry("mot_left_enc", mot_left_enc.getValue())
        send_telemetry("mot_right_enc", mot_right_enc.getValue())
        send_telemetry("odo_left", odo_left.getValue())
        send_telemetry("odo_right", odo_right.getValue())

        mot_left.setVelocity(left)
        mot_right.setVelocity(right)

if __name__ == "__main__":
    main()
