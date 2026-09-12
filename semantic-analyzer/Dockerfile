FROM python:3.11-slim

# Install Java (for ANTLR4 tool) and graphviz (for AST rendering)
RUN apt-get update && apt-get install -y \
  default-jdk-headless \
  graphviz \
  curl \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /compiscript

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download ANTLR4 jar
RUN curl -sSL https://www.antlr.org/download/antlr-4.13.2-complete.jar \
  -o antlr-4.13.2-complete.jar

# Copy project files
COPY . .

# Generate ANTLR4 parser files
RUN mkdir -p compiler/generated && \
    java -jar antlr-4.13.2-complete.jar \
      -Dlanguage=Python3 \
      -visitor -listener \
      -o compiler/generated \
      compiler/Compiscript.g4 && \
    touch compiler/generated/__init__.py

# Expose IDE port
EXPOSE 5000

ENV HOST=0.0.0.0
ENV PORT=5000

# Default: launch the IDE
CMD ["python3", "ide/server.py"]
