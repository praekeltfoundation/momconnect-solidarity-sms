FROM praekeltfoundation/python-base:3.7.3-stretch

COPY requirements.txt .
RUN pip install -r requirements.txt

ENTRYPOINT ["tini", "--", "sanic", "api.app", "--host=0.0.0.0"]

COPY api.py .
