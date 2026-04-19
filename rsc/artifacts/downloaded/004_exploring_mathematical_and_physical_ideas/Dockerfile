FROM python:3.12-slim

WORKDIR /papers

RUN pip install reportlab==4.2.2

COPY paper1_v5.py .
COPY paper2_v4.py .
COPY build.sh .

RUN chmod +x build.sh

CMD ["./build.sh"]
