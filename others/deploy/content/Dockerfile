FROM python:3.13.16-slim@sha256:cf50a4f6ac4f026458b08d5222023d700ac806410dff5e9ca8728fa44f2b850f
WORKDIR /parser
COPY requirements.txt /parser/requirements.txt
RUN pip install --no-cache-dir --require-hashes --only-binary=:all: -r requirements.txt
COPY content/ /parser/content/
COPY container_entry.py /parser/container_entry.py
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 LANG=C.UTF-8
USER 65532:65532
ENTRYPOINT ["python", "/parser/container_entry.py"]
