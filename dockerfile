FROM mcr.microsoft.com/azure-functions/python:4-python3.10

# Install dependencies
RUN apt-get update && apt-get install -y \
    gnupg \
    curl \
    unixodbc \
    unixodbc-dev \
    gcc \
    g++ \
    libpq-dev \
    libssl-dev \
    libsasl2-dev \
    libkrb5-dev \
    libldap2-dev \
    libodbc1 \
    odbcinst \
    # Microsoft ODBC 18 Driver
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Ensure pip, wheel, setuptools are updated
RUN pip install --upgrade pip setuptools wheel

# Install Python dependencies
COPY requirements.txt /
RUN pip install -r /requirements.txt

# Copy your Azure Function App code
COPY . /home/site/wwwroot
