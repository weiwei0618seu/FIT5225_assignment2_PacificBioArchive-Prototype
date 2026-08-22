FROM public.ecr.aws/lambda/python:3.12-x86_64 AS classifier-builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY backend/requirements-convert.txt /tmp/requirements-convert.txt
RUN python -m pip install --upgrade pip==25.2 && \
    python -m pip install --requirement /tmp/requirements-convert.txt && \
    python -m pip check
COPY backend/scripts/export_classifier.py /tmp/export_classifier.py
COPY legacy/PacificBioArchive/model.pt /tmp/model.pt
RUN python /tmp/export_classifier.py /tmp/model.pt /opt/build/model.torchscript

FROM public.ecr.aws/lambda/python:3.12-x86_64

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY backend/requirements-ml.txt /tmp/requirements-ml.txt
RUN python -m pip install --upgrade pip==25.2 && \
    python -m pip install --requirement /tmp/requirements-ml.txt && \
    python -m pip check && \
    rm -rf /root/.cache /tmp/requirements-ml.txt

COPY backend/src/pacific_bioarchive ${LAMBDA_TASK_ROOT}/pacific_bioarchive
COPY legacy/PacificBioArchive/mdv5a.pt /opt/models/mdv5a.pt
COPY --from=classifier-builder /opt/build/model.torchscript /opt/models/model.torchscript
COPY legacy/PacificBioArchive/labels.txt /opt/models/labels.txt

RUN python -c "from pathlib import Path; from pacific_bioarchive.ml.labels import SpeciesLabelMap; labels=SpeciesLabelMap.from_file(Path('/opt/models/labels.txt')); assert len(labels) == 46" && \
    python -c "import torch; model=torch.jit.load('/opt/models/model.torchscript', map_location='cpu'); assert tuple(model(torch.zeros((1,480,480,3))).shape) == (1,46)" && \
    python -c "import shutil; from pathlib import Path; root=Path('${LAMBDA_TASK_ROOT}/pacific_bioarchive'); [shutil.rmtree(path) for path in root.rglob('__pycache__')]"

CMD ["pacific_bioarchive.handlers.media_processor.lambda_handler"]
