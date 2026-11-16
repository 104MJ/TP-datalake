FROM python:3.11-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_LINK_MODE=copy \
    HADOOP_USER_NAME=root \
    JAVA_HOME=/usr/lib/jvm/default-java \
    PATH="/usr/lib/jvm/default-java/bin:${PATH}" \
    PYSPARK_PYTHON=python3 \
    PYSPARK_DRIVER_PYTHON=python3

RUN apt-get update && apt-get install -y --no-install-recommends \
    default-jre-headless \
    libsnappy1v5 \
    git \
    jq \
    procps \
    htop \
    curl \
    less \
    nano \
    bash-completion \
    iputils-ping \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/* \
    && (test -e /usr/lib/jvm/default-java || ln -s "/usr/lib/jvm/java-17-openjdk-$(dpkg --print-architecture)" /usr/lib/jvm/default-java) \
    && git config --system --add safe.directory /workspace

WORKDIR /workspace

COPY requirements.txt /tmp/requirements.txt
RUN uv pip install --system --no-cache -r /tmp/requirements.txt && \
    python3 -m ipykernel install --sys-prefix --name python3 --display-name "Python 3.11 (PySpark 3.5 + Delta Lake)" && \
    python3 -c "from pyspark.sql import SparkSession; \
    SparkSession.builder \
    .master('local[1]') \
    .config('spark.driver.extraJavaOptions', '-XX:+IgnoreUnrecognizedVMOptions -XX:UseSVE=0') \
    .config('spark.jars.packages', 'io.delta:delta-spark_2.12:3.2.1') \
    .getOrCreate().stop()"

# Métadonnées Dev Container intégrées à l'image (actives aussi via "Attach Visual Studio Code" sur spark-jupyter)
LABEL devcontainer.metadata='[{"customizations":{"vscode":{"extensions":["ms-python.python","ms-python.vscode-pylance","ms-python.debugpy","charliermarsh.ruff","ms-toolsai.jupyter","ms-toolsai.jupyter-keymap","ms-toolsai.jupyter-renderers","mechatroner.rainbow-csv","redhat.vscode-xml","redhat.vscode-yaml"],"settings":{"python.defaultInterpreterPath":"/usr/local/bin/python3","jupyter.kernels.trusted":["/usr/local/share/jupyter/kernels/python3/kernel.json"]}}}}]'
