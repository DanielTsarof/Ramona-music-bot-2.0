FROM ubuntu:latest
LABEL authors="danila"

ENTRYPOINT ["top", "-b"]