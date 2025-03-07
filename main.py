from bosdyn import client
from camera import depth_video
from bosdyn.client.sdk import create_standard_sdk
import bosdyn
import bosdyn.client
def main():
    #add spots username and password to authenticate with the robot
    username = ''
    password = ''
    address = ''
    sdk = bosdyn.client.create_standard_sdk('client')
    robot = sdk.create_robot(address)
    #authenticate with the robot
    token =robot.authenticate(username,password)
    #stream video from spots depth sensors
    depth_video(robot,'frontright')

    
    


main()