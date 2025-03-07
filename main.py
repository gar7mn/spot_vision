from bosdyn import client
import bosdyn.client
from bosdyn.client.sdk import create_standard_sdk
import bosdyn
def main():
    username = ''
    password = ''
    sdk = bosdyn.client.create_standard_sdk('client')
    robot = sdk.create_robot('192.168.80.3')
    #authenticate with the robot
    token =robot.authenticate(username,password)
    
    
    return