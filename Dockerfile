FROM python:3.11

ADD . /app
WORKDIR /app

# Allow execution of run script
RUN chmod +x run_web.sh

# Install requirements
RUN pip install -r requirements.txt