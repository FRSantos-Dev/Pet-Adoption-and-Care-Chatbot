FROM mcr.microsoft.com/devcontainers/python:3.11


RUN apt-get update && apt-get install -y \
    postgresql \
    postgresql-contrib \
    && rm -rf /var/lib/apt/lists/*


RUN service postgresql start && \
    sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'postgres';"


ENV DB_NAME=pet_adoption
ENV DB_USER=postgres
ENV DB_PASSWORD=postgres
ENV DB_HOST=localhost
ENV DB_PORT=5432


RUN useradd -m -s /bin/bash vscode && \
    usermod -aG sudo vscode


WORKDIR /workspace


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


COPY . .


RUN chown -R vscode:vscode /workspace


USER vscode 