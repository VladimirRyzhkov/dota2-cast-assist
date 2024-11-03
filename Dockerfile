# This image has an auto-tuning mechanism included to start
# a number of worker processes based on the available CPU cores
FROM tiangolo/uvicorn-gunicorn-fastapi:python3.11

# Install system dependencies and useful tools
RUN apt-get update && apt-get install -y vim htop

# Expose port 8080
EXPOSE 8080
ENV PORT 8080

## Set a default value for SERVICE_NAME
ARG SERVICE_NAME=dota2-cast-assist
ENV SERVICE_NAME=${SERVICE_NAME}

# Copy your application code
COPY app /app
COPY common /common
COPY events_processor/libs/firestore.py /events_processor/libs/firestore.py
COPY live_matches_crawler /live_matches_crawler
COPY healthcheck /healthcheck
COPY ./pyproject.toml /app/pyproject.toml
COPY ./poetry.lock /app/poetry.lock
RUN chmod +x /app/prestart.sh
RUN chmod +x /app/start.sh

# Install Poetry
ENV POETRY_HOME="/opt/poetry"
ENV PATH="$POETRY_HOME/bin:/usr/local/bin:$PATH"

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Configure Poetry to not create virtual environments
RUN poetry self update
RUN poetry config virtualenvs.create false

# Set the HEALTHCHECK instruction
RUN chmod +x /healthcheck/healthcheck.sh
HEALTHCHECK --interval=1m --timeout=30s --start-period=30s --retries=3 CMD /healthcheck/healthcheck.sh

# Set the working directory in the container
WORKDIR /app

ENV PYTHONPATH="${PYTHONPATH}:/"

CMD ["bash", "/app/start.sh"]
