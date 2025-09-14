# Use a slim Python 3.12 image to keep the container size small.
FROM python:3.12-slim

# Set the working directory inside the container.
WORKDIR /app

# Install system dependencies and the `uv` package manager for fast installations.
# Using a single `RUN` command reduces the number of layers in the Docker image.
RUN apt-get update \
    && apt-get install -y curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to the PATH to make the `uv` command available.
ENV PATH="/root/.local/bin:${PATH}"

# Copy the requirements file into the container.
COPY requirements.txt .

# Install dependencies from the requirements file using uv.
# The `--system` flag ensures packages are installed into the system site-packages.
RUN uv pip install --system -r requirements.txt \
    && mkdir -p /app/storage

# Copy the rest of the application code into the container.
COPY . .

# Define a volume for persistent storage of user-generated data.
# This ensures data is not lost when the container is removed.
VOLUME ["/app/storage"]

# Expose the port the application will run on.
EXPOSE 8080

# The command to run the application using uvicorn.
# It runs the application directly, which is the best practice for Docker.
# The `reload=True` from your previous code is for development only and should not be used in production.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
