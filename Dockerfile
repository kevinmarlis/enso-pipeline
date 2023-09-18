FROM osgeo/proj

RUN apt-get update \
    && apt-get install -y gcc build-essential python3-dev libproj-dev proj-bin proj-data\
    && apt-get install -y libgeos-dev\
    && apt-get install -y wget python3-pip vim\
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
ENV DEBIAN_FRONTEND=noninteractive
RUN echo ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true | debconf-set-selections
RUN apt-get update  && DEBIAN_FRONTEND=noninteractive\
    && apt-get install msttcorefonts -qq\
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
WORKDIR /pipeline
CMD [ "python3", "run_pipeline.py" ]