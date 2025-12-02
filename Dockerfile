# Use the exact base OS from production
FROM ubuntu:22.04

# Set the frontend to non-interactive to avoid prompts
ENV DEBIAN_FRONTEND=noninteractive

# Update apt and install all build dependencies in one layer
# This is the most critical step
RUN apt-get update && apt-get install -y \
    build-essential \
    software-properties-common \
    git \
    curl \
    # Add the PPA to get the exact Python version
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    # Install the *exact* Python, its dev headers, and the *exact* GCC
    && apt-get install -y \
    python3.10-dev \
    python3.10-venv \
    python3-pip \
    gcc-11 \
    g++-11 \
    # Clean up apt lists to keep the image small
    && rm -rf /var/lib/apt/lists/*

# Set python3.10 and gcc-11 as the defaults
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1 \
    && update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-11 110 \
    && update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-11 110

# Verify the versions (this is just for your peace of mind)
RUN python --version \
    && pip --version \
    && gcc --version

# Set the working directory inside the container
WORKDIR /app

# Copy your requirements and install them
COPY requirements.txt .
RUN pip install -r requirements.txt

# Keep the container running so you can attach to it
CMD ["tail", "-f", "/dev/null"]
