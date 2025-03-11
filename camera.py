from bosdyn.client import Sdk,BaseClient,image,Robot,create_standard_sdk
from bosdyn.client.server_util import GrpcServiceRunner
from bosdyn.client.image import ImageClient,build_image_request
from bosdyn.client.directory_registration import DirectoryRegistrationClient,DirectoryRegistrationKeepAlive
from bosdyn.api import image_pb2,image_pb2_grpc,image_service_pb2,image_service_pb2_grpc
from bosdyn.client.image_service_helpers import CameraInterface,CameraBaseImageServicer
from bosdyn.client import log_status
# from detection import inference_image
from bosdyn.client.time_sync import TimedOutError
from scipy import ndimage
# from detection import inference_image
import numpy as np
import cv2
import time
import io
import sys
import logging


"""Captures Images from the robot"""
RGB = 'PIXEL_FORMAT_RGB_U8'
GREY = 'PIXEL_FORMAT_GREYSCALE_U8'
DEPTH = 'PIXEL_FORMAT_DEPTH_U16'


def create_image_requests(source:str):
    rgb_req = image.build_image_request(source,90,None,pixel_format=RGB)
    greyreq= image.build_image_request(source,90,None,GREY)
    # depthreq = image.build_image_request(sou)
    return rgb_req,greyreq



ROTATION_ANGLE = {
    'back_fisheye_image': 0,
    'frontleft_fisheye_image': -90,
    'frontright_fisheye_image': -90,
    'left_fisheye_image': 0,
    'right_fisheye_image': 180
}
VALUE_FOR_Q_KEYSTROKE = 113
VALUE_FOR_ESC_KEYSTROKE = 27



def image_to_opencv(image,auto_rotate=True):
    num_channels =1 # assume image is 1 channels
    #handle each kind of pixel format
    if image.shot.image.pixel_format == image_pb2.Image.PIXEL_FORMAT_DEPTH_U16:
         dtype = np.uint16
         extension = '.png'
    else:
        dtype = np.uint8
        if image.shot.image.pixel_format == image_pb2.Image.PIXEL_FORMAT_RGB_U8:
            num_channels = 3
        elif image.shot.image.pixel_format == image_pb2.Image.PIXEL_FORMAT_GREYSCALE_U8:
            num_channels = 1
        extension = '.jpg'
    img = np.frombuffer(image.shot.image.data,dtype=dtype)
    if image.shot.image.format == image_pb2.Image.FORMAT_RAW:
         try:
              #try to reshape the image
              img = img.reshape((image.shot.image.rows, image.shot.image.cols,num_channels))
         except ValueError:
              #unable to reshape image data try rectangular decode

              img = cv2.imdecode(img,-1)
    else: 
         img = cv2.imdecode(img,-1)
    if auto_rotate:
         img  = ndimage.rotate(img,ROTATION_ANGLE[image.source.name])
    return img,extension


def depth_to_opencv(image, auto_rotate=True):
    extension = '.png'
    dtype = np.uint16
    # print(type(image[0]))

    # Convert depth image
    cv_depth = np.frombuffer(image[0].shot.image.data, dtype=dtype)
    cv_depth = cv_depth.reshape(image[0].shot.image.rows, image[0].shot.image.cols)

    # Convert visual image
    cv_visual = cv2.imdecode(np.frombuffer(image[1].shot.image.data, np.uint8), -1)
    visual_rgb = cv_visual if len(cv_visual.shape) == 3 else cv2.cvtColor(cv_visual, cv2.COLOR_GRAY2RGB)

    # Normalize depth image to uint8
    min_val = np.min(cv_depth)
    max_val = np.max(cv_depth)
    depth_range = max_val - min_val
    depth8 = (255.0 / depth_range * (cv_depth - min_val)).astype('uint8')

    # Convert depth to RGB
    depth8_rgb = cv2.cvtColor(depth8, cv2.COLOR_GRAY2RGB)
    depth_color = cv2.applyColorMap(depth8_rgb, cv2.COLORMAP_JET)

    # Overlay depth on visual image
    out = cv2.addWeighted(visual_rgb, 0.4, depth_color, 0.6, 0)

    # Rotate image if needed
    # if auto_rotate:
    #     if image[0].source.name == 'front':
    #         out = ndimage.rotate(out,ROTATION_ANGLE[image.source.name])
    #         # out = cv2.rotate(out, cv2.ROTATE_90_CLOCKWISE)
    #     elif image[0].source.name == 'right':
    #         out = ndimage.rotate(out,ROTATION_ANGLE[image.source.name])
    #         out = cv2.rotate(out,cv2.ROTATE_90_COUNTERCLOCKWISE)
    return out, extension



def depth_video(robot: Robot,cam:str='frontleft'):
    """Capture video from Spot's depth sensors and overlay it with the regular camera.
    
    robot:
        Authenticated robot object that represents the spot robot.
    
    cam: 
        either frontleft,frontright,left or right if None it will choose frontleft"""
    #will use the frontleft sensors by default
    
    sources = [cam+'_depth_in_visual_frame', cam+'_fisheye_image']
    image_client = robot.ensure_client(ImageClient.default_service_name)
    requests = [build_image_request(source, 100) for source in sources]

    for source in sources:
        cv2.namedWindow(source, cv2.WINDOW_GUI_NORMAL)
        if len(sources) > 2:
            cv2.setWindowProperty(source, cv2.WND_PROP_AUTOSIZE, cv2.WINDOW_AUTOSIZE)
        else:
            cv2.setWindowProperty(source, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    keystroke = None
    timeout_count_before_reset = 0
    timeout_before_reset = None
    t1 = time.time()
    image_count = 0

    while keystroke != ord('q') and keystroke != 27:  # 'q' key or ESC key
        try:
            image_future = image_client.get_image_async(requests, timeout=0.5)
            
            while not image_future.done():
                keystroke = cv2.waitKey(25)
                if keystroke == ord('q') or keystroke == 27:  # Exit if 'q' or ESC is pressed
                    sys.exit(0)
                time.sleep(0.01)
            
            images = image_future.result()
            
            # Process each ImageResponse object
            if len(images) == 2:  # Ensure we have exactly two images as expected
                image_list = [images[0], images[1]]  # Create a list of ImageResponse objects
                overlay_image, _ = depth_to_opencv(image_list, True)
                cv2.imshow('video', overlay_image)
                cv2.waitKey(1)

        except Exception as exc:
            print(exc)

    cv2.destroyAllWindows()
