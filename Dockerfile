FROM python:3.6.9

WORKDIR /usr/app

RUN apt-get update -y 
RUN apt-get -y install gcc
RUN pip install --upgrade pip
RUN pip install Cython
RUN pip install numpy==1.19.5
RUN pip install cmake

COPY requirements.txt ./
RUN pip install --no-cache -r requirements.txt
RUN pip install opencv-python-headless==4.5.2.52

COPY . ./

ENV PYTHONUNBUFFERED=1
ENV PYTHON_ENV=prod

ENTRYPOINT ["python3", "app.py"]
