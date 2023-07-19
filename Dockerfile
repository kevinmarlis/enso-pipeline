FROM continuumio/miniconda3

# RUN apt-get update \
#     && apt-get install -y gcc build-essential python3.9-dev libproj-dev proj-bin proj-data\
#     && apt-get install -y libgeos-dev\
#     && apt-get install -y wget python3-pip vim\
#     && apt-get clean \
#     && rm -rf /var/lib/apt/lists/*
COPY evinronment.yaml .

RUN conda env create -f environment.yml
COPY . .
WORKDIR /pipeline
CMD [ "conda", "activate", "enso_pipeline", "python", "run_pipeline" ]