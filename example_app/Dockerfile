FROM jjanzic/docker-python3-opencv

# Twilio environment variables for text notifications
# run `source twilio.env` prior to building image
ARG twilio_account_sid
ENV TWILIO_ACCOUNT_SID=${twilio_account_sid}
ARG twilio_auth_token
ENV TWILIO_AUTH_TOKEN=${twilio_auth_token}
ARG twilio_outgoing
ENV TWILIO_OUTGOING=${twilio_outgoing}
ARG twilio_recipient
ENV TWILIO_RECIPIENT=${twilio_recipient}

RUN mkdir /app
WORKDIR /app

RUN pip install opencv-contrib-python zmq imutils twilio

ADD face_rec_server.py haarcascade_frontalface_default.xml ./
ADD config ./
ADD trainer ./trainer
ADD imagezmq ./imagezmq

CMD python3 face_rec_server.py