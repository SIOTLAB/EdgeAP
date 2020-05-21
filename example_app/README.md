# Example Application

Face recognition for video streams.

## Overview

A Logitech webcam attached to a Raspberry Pi 3 captures video and streams it to an application on a nearby access point.
The application performs face recognition and alerts the owner via a text message when a person is identified. If the person
identified is a registered user that the ML model was trained on, then the text will provide his/her name. Otherwise, the text
will notify of a stranger.

## Configuration

To configure which users should be identified, edit `config` with the list of user ids:
```
{
    "ids": ["Cyrus", "Philip", "Jake", "Michael", "Chris", "Justin"]
}
```

To configure Twilio text notifications, edit `twilio.env` with your twilio account credentials:
```
export TWILIO_ACCOUNT_SID='xxxxxx'
export TWILIO_AUTH_TOKEN='xxxxxx'
export TWILIO_RECIPIENT='+12223334444'
export TWILIO_OUTGOING='+15556667777'
```

Make sure to source your credentials prior to building/running the application:\
`source ./twilio.env`

## Local Development

Note: Must install opencv2 first. Also, install prerequisites: `pip3 install -r requirements.txt`

1. Collect image data for the users specified in `config`\
`python3 face_dataset.py`

2. Train the face classifier based on the dataset of users\
`python3 face_training.py`

3. Recognize faces locally\
`python3 faceRecognition.py`

4. Recognize faces localy and test text notifications\
`python3 faceRecognition_notifications.py`

## Integration with EdgeAP

The client (Raspberry Pi) will capture the video and send it to the server (AP) for processing. Currently using the [imagezmq](https://github.com/jeffbass/imagezmq) library for transporting OpenCV images. The server running on the AP is deployed as a Docker container.

## Build image

```
source ./twilio.env
docker build . \
    --build-arg twilio_account_sid=$TWILIO_ACCOUNT_SID \
    --build-arg twilio_auth_token=$TWILIO_AUTH_TOKEN \
    --build-arg twilio_outgoing=$TWILIO_OUTGOING \
    --build-arg twilio_recipient=$TWILIO_RECIPIENT \
    --file Dockerfile --tag image-name
```

## Run Video Streaming Application

Make sure the EdgeAP management server is up and running.
Then, on the Raspberry Pi 3, run the following program to instantiate the container on the AP and begin streaming video to it:
```
pip3 install -r requirements.txt
python3 video_client.py
```