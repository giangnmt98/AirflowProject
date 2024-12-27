import argparse


def generate_dockerfile(
        docker_file_name="Dockerfile",
        ubuntu_version="22.04",
        conda_version="2023.07-0",
        conda_env_name="py3.9",
        python_version="3.9",
        jdk_version="11",
        cuda_version=None,
        redis_version=None,
        redis_password=None,
        mysql_version=None,
        mysql_user=None,
        mysql_password=None
):
    dockerfile_content = f"""# Use Ubuntu as the base image
ARG UBUNTU_VERSION={ubuntu_version}
FROM ubuntu:${{UBUNTU_VERSION}}

# Set environment variables for non-interactive installation
ENV DEBIAN_FRONTEND=noninteractive

# Update and install dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    git \
    build-essential \
    ca-certificates \
    software-properties-common \
    gnupg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Anaconda
ARG CONDA_VERSION={conda_version}
ENV CONDA_DIR /opt/conda
RUN wget --quiet https://repo.anaconda.com/archive/Anaconda3-${{CONDA_VERSION}}-Linux-x86_64.sh -O /tmp/anaconda.sh && \
    bash /tmp/anaconda.sh -b -p $CONDA_DIR && \
    rm /tmp/anaconda.sh && \
    $CONDA_DIR/bin/conda clean -afy

# Update PATH environment variable
ENV PATH=$CONDA_DIR/bin:$PATH
RUN conda init bash && . ~/.bashrc

# Create a new Anaconda environment
ARG CONDA_ENV_NAME={conda_env_name}
ARG PYTHON_VERSION={python_version}
RUN conda create -n $CONDA_ENV_NAME python=${{PYTHON_VERSION}} -y && \
    conda clean -afy

# Activate the new environment by default
RUN echo \"conda activate $CONDA_ENV_NAME\" >> ~/.bashrc
ENV PATH=$CONDA_DIR/envs/$CONDA_ENV_NAME/bin:$PATH

# Install JDK
ARG JDK_VERSION={jdk_version}
RUN conda install -n $CONDA_ENV_NAME openjdk=${{JDK_VERSION}} -c conda-forge -y && \
    conda clean -afy

"""
    if cuda_version:
        dockerfile_content += f"""# Install CUDA
ARG CUDA_VERSION={cuda_version}
RUN conda install -n $CONDA_ENV_NAME cuda=${{CUDA_VERSION}} -c nvidia/label/cuda-${{CUDA_VERSION}} -y && \
    conda clean -afy
"""

    if redis_version:
        dockerfile_content += f"""# Install Redis
ARG REDIS_VERSION={redis_version}
RUN apt-get update && apt-get install -y redis-server=${{REDIS_VERSION}} && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
"""
    if redis_password:
        dockerfile_content += f"""# Configure Redis
    RUN echo \"requirepass '{redis_password}'\" >> /etc/redis/redis.conf && \
        echo \"bind 0.0.0.0\" >> /etc/redis/redis.conf
    """

    if mysql_version and mysql_user and mysql_password:
        dockerfile_content += f"""# Install MySQL
ARG MYSQL_VERSION={mysql_version}
RUN apt-get update && apt-get install -y mysql-server=${{MYSQL_VERSION}} && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Configure MySQL
RUN service mysql start && \
    mysql -e \"CREATE USER IF NOT EXISTS '{mysql_user}'@'%' IDENTIFIED BY '{mysql_password}';\" && \
    mysql -e \"GRANT ALL PRIVILEGES ON *.* TO '{mysql_user}'@'%' WITH GRANT OPTION;\" && \
    mysql -e \"FLUSH PRIVILEGES;\"
"""

    dockerfile_content += f"""# Set default shell to bash
SHELL [\"/bin/bash\", \"-c\"]

# Set working directory
WORKDIR /workspace

# Default command
CMD [\"/bin/bash\"]
"""

    with open(docker_file_name, "w") as file:
        file.write(dockerfile_content)
    print("Dockerfile generated successfully.")



def main():
    parser = argparse.ArgumentParser(description="Generate a Dockerfile with specified parameters.")
    parser.add_argument("--docker_file_name", default="Dockerfile", help="Docker file name (default: Dockerfile)")
    parser.add_argument("--ubuntu_version", default="22.04", help="Ubuntu version (default: 22.04)")
    parser.add_argument("--conda_version", default="2023.07-0", help="Conda version (default: 2023.07-0)")
    parser.add_argument("--conda_env_name", default="py3.9", help="Name of the Conda environment (default: py3.9)")
    parser.add_argument("--python_version", default="3.9", help="Python version (default: 3.9)")
    parser.add_argument("--jdk_version", default="11", help="JDK version (default: 11)")
    parser.add_argument("--cuda_version", default="12.2.0", help="CUDA version (if not set, CUDA installation will be skipped)")
    parser.add_argument("--redis_version", default=None, help="Redis version (if not set, Redis installation will be skipped)")
    parser.add_argument("--redis_password", default=None, help="Redis password (if not set, Redis password configuration will be skipped)")
    parser.add_argument("--mysql_version", default=None, help="MySQL version (if not set, MySQL installation will be skipped)")
    parser.add_argument("--mysql_user", default=None, help="MySQL user (required if MySQL is installed)")
    parser.add_argument("--mysql_password", default=None, help="MySQL password (required if MySQL is installed)")

    args = parser.parse_args()
    print("=" * 50)
    print("Creating Dockerfile...")
    print("Docker file name: ", args.docker_file_name)
    print("Ubuntu version: ", args.ubuntu_version)
    print("Conda version: ", args.conda_version)
    print("Conda environment name: ", args.conda_env_name)
    print("Python version: ", args.python_version)
    print("JDK version: ", args.jdk_version)
    if args.cuda_version is not None:
        print("CUDA version: ", args.cuda_version)
    if args.redis_version is not None:
        print("Redis version: ", args.redis_version)
    if args.redis_password is not None:
        print("Redis password: ", args.redis_password)
    if args.mysql_version is not None:
        print("MySQL version: ", args.mysql_version)
    if args.mysql_user is not None:
        print("MySQL user: ", args.mysql_user)
    if args.mysql_password is not None:
        print("MySQL password: ", args.mysql_password)
    print("Successfully created Dockerfile.")
    print("=" * 50)

    generate_dockerfile(
        docker_file_name=args.docker_file_name,
        ubuntu_version=args.ubuntu_version,
        conda_version=args.conda_version,
        conda_env_name=args.conda_env_name,
        python_version=args.python_version,
        jdk_version=args.jdk_version,
        cuda_version=args.cuda_version,
        redis_version=args.redis_version,
        redis_password=args.redis_password,
        mysql_version=args.mysql_version,
        mysql_user=args.mysql_user,
        mysql_password=args.mysql_password
    )


if __name__ == "__main__":
    main()
