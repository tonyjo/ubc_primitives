#!/bin/bash

# Run Pipeline
echo "Running in local docker image for testing"

sudo docker run -v /home/tony/Documents/work_plai/d3m/codes/ubc_primitives:/ubc_primitives\
                -i -t ab7b415b3799 /bin/bash \
                -c "cd /ubc_primitives;\
                    pip3 install -e .;\
                    cd pipelines;\
                    python3 smi_pipeline.py
                    python3 -m d3m runtime --volumes /ubc_primitives/primitives/smi/weights fit-produce \
                            -p semantic_type_pipeline.json \
                            -r /ubc_primitives/datasets/seed_datasets_current/38_sick/TRAIN/problem_TRAIN/problemDoc.json \
                            -i /ubc_primitives/datasets/seed_datasets_current/38_sick/TRAIN/dataset_TRAIN/datasetDoc.json \
                            -t /ubc_primitives/datasets/seed_datasets_current/38_sick/TEST/dataset_TEST/datasetDoc.json \
                            -o results.csv \
                            -O pipeline_run.yml;\
                    exit"
