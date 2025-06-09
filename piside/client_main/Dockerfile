FROM debian:bookworm-slim

RUN apt update && apt install -y curl git git-lfs make  && apt clean

RUN curl https://get.volta.sh | bash

ENV VOLTA_HOME=/root/.volta
ENV PATH=${VOLTA_HOME}/bin:${PATH}
ADD package.json /workspace/
ADD package-lock.json /workspace/
WORKDIR /workspace
RUN node -v
