FROM node:20-bullseye

USER root
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python-is-python3 \
        make \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g n8n

COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install -r /tmp/requirements.txt

USER node
WORKDIR /home/node

EXPOSE 5678
CMD ["n8n"]
