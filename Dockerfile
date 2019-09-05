FROM jfloff/alpine-python
ADD . .
RUN pip install -r requirements.txt
CMD [ "python", "./worker.py" ]
