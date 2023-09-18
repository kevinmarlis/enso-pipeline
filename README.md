# Sea Level Indicators

A containerized version of the Sea Level Indicators data pipeline that calculates El Niño Southern Oscillation, Pacific Decadal Oscillation and Indian Ocean Diple sea level indicator values from along track satellite data.

## Getting Started

Clone the repo: https://github.com/kevinmarlis/enso-pipeline

Pulling the image: `docker pull kmarlis/enso-pipeline:latest`

## Executing the container

The pipeline requires mounting two directories: one containing the alongtrack data, and one containing the pipeline output. 

```
docker run --rm -dit -v /export/01/dev-data3/alongtrack-delivery/:/alongtrack-delivery -v /home/marlis/pipeline_output:/pipeline_output kmarlis/enso-pipeline:latest
```

This will mount the appropriate directories and will execute the pipeline end to end. There are checks in place so that redundant work will not be performed.

## Links
Indicators can be found at https://sealevel.jpl.nasa.gov