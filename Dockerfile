FROM public.ecr.aws/docker/library/python:3.11-slim

WORKDIR /usr/src/app

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

RUN mkdir -p ./data/images

COPY streamlit_app.py streamlit_app.py
COPY utils.py utils.py
COPY .env .env

EXPOSE 80

ENTRYPOINT ["streamlit", "run", "streamlit_app.py", "--server.port=80", "--server.address=0.0.0.0", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]