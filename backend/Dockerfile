FROM nvidia/cuda:11.7.1-cudnn8-devel-ubuntu22.04

USER root

WORKDIR /app

EXPOSE 8080

RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y git build-essential \
    python3 python3-pip gcc wget \
    ocl-icd-opencl-dev opencl-headers clinfo \
    libclblast-dev libopenblas-dev curl\
    && mkdir -p /etc/OpenCL/vendors && echo "libnvidia-opencl.so.1" > /etc/OpenCL/vendors/nvidia.icd
    
ENV CUDA_DOCKER_ARCH=all

RUN python3 -m pip install --upgrade pip

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements_r2.txt

RUN pip install accelerate
RUN pip install torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload", "--log-level", "debug"]