#!/bin/bash

NAME=elg_faro
TAG=1.0.0
docker build -f Dockerfile.ELG -t ${NAME}:${TAG} .
