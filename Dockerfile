# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    wget \
    unzip \
    tk \
    tcl \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Define EnergyPlus version and install it
ARG ENERGYPLUS_VERSION="22.2.0"
ARG ENERGYPLUS_SHA="c249759bad"

# Install EnergyPlus
RUN wget "https://github.com/NREL/EnergyPlus/releases/download/v${ENERGYPLUS_VERSION}/EnergyPlus-${ENERGYPLUS_VERSION}-${ENERGYPLUS_SHA}-Linux-Ubuntu20.04-x86_64.tar.gz" && \
    tar -xzvf "EnergyPlus-${ENERGYPLUS_VERSION}-${ENERGYPLUS_SHA}-Linux-Ubuntu20.04-x86_64.tar.gz" -C /usr/local/ && \
    rm "EnergyPlus-${ENERGYPLUS_VERSION}-${ENERGYPLUS_SHA}-Linux-Ubuntu20.04-x86_64.tar.gz"

ENV ENERGYPLUS_EXE_PATH="/usr/local/EnergyPlus-${ENERGYPLUS_VERSION}/energyplus"
ENV ENERGYPLUS_VERSION=${ENERGYPLUS_VERSION}

# Copy the rest of the application
COPY . .

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Command to run the application
CMD ["python", "main.py"]
