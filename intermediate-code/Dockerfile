FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    default-jdk-headless \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN curl -sSL https://www.antlr.org/download/antlr-4.13.2-complete.jar \
    -o antlr-4.13.2-complete.jar

COPY . .

RUN pip install --no-cache-dir -e .

RUN mkdir -p src/compiscript/generated && \
    java -jar antlr-4.13.2-complete.jar \
      -Dlanguage=Python3 -visitor -no-listener \
      -o src/compiscript/generated \
      grammar/Compiscript.g4 && \
    touch src/compiscript/generated/__init__.py

EXPOSE 8501
ENV PYTHONPATH=/app/src

CMD ["streamlit", "run", "src/compiscript/ide/app.py", "--server.address=0.0.0.0"]
