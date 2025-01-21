import argparse


def generate_dockerfile(
        docker_file_name="Dockerfile",
        ubuntu_version="22.04",
        conda_version="2023.07-0",
        conda_env_name="py3.9",
        python_version="3.9",
        jdk_version="11",
        cuda_version=None
):
    dockerfile_content = f"""# Use Ubuntu as the base image
ARG UBUNTU_VERSION={ubuntu_version}
FROM ubuntu:${{UBUNTU_VERSION}}

# Set environment variables for non-interactive installation
ENV DEBIAN_FRONTEND=noninteractive

# Update and install dependencies
RUN apt-get update && apt-get install -y \\
    wget \\
    curl \\
    git \\
    build-essential \\
    ca-certificates \\
    software-properties-common \\
    gnupg \\
    && apt-get clean \\
    && rm -rf /var/lib/apt/lists/*

# Install Anaconda
ARG CONDA_VERSION={conda_version}
ENV CONDA_DIR=/opt/conda
RUN wget --quiet https://repo.anaconda.com/archive/Anaconda3-${{CONDA_VERSION}}-Linux-x86_64.sh -O /tmp/anaconda.sh && \\
    bash /tmp/anaconda.sh -b -p $CONDA_DIR && \\
    rm /tmp/anaconda.sh && \\
    $CONDA_DIR/bin/conda clean -afy

# Update PATH environment variable
ENV PATH=$CONDA_DIR/bin:$PATH
RUN conda init bash && . ~/.bashrc

# Create a new Anaconda environment
ARG CONDA_ENV_NAME={conda_env_name}
ARG PYTHON_VERSION={python_version}
RUN conda create -n $CONDA_ENV_NAME python=${{PYTHON_VERSION}} -y && \\
    conda clean -afy

# Activate the new environment by default
RUN echo \"conda activate $CONDA_ENV_NAME\" >> ~/.bashrc
ENV PATH=$CONDA_DIR/envs/$CONDA_ENV_NAME/bin:$PATH

# Install JDK
ARG JDK_VERSION={jdk_version}
RUN conda install -n $CONDA_ENV_NAME openjdk=${{JDK_VERSION}} -c conda-forge -y && \\
    conda clean -afy

"""
    if cuda_version:
        dockerfile_content += f"""# Install CUDA
ARG CUDA_VERSION={cuda_version}
RUN conda install -n $CONDA_ENV_NAME cuda=${{CUDA_VERSION}} -c nvidia/label/cuda-${{CUDA_VERSION}} -y && \\
    conda clean -afy
"""

    # Tạo user và thiết lập quyền
    dockerfile_content += """# Tạo group với ID 1000 nếu chưa tồn tại
RUN groupadd -g 1000 customgroup

# Tạo user "docker" và thêm vào group với ID 1000
RUN useradd -m -g 1000 docker

# Thiết lập quyền để user "docker" có thể truy cập conda
RUN echo "source /opt/conda/bin/activate" >> /home/docker/.bashrc

# Đặt quyền cho thư mục home của user docker
RUN chown -R docker:customgroup /home/docker

# Chuyển quyền sử dụng container về user "docker"
USER docker
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
    )


if __name__ == "__main__":
    main()