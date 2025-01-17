import argparse
import yaml
import subprocess


def save_file(content: str, path: str) -> None:
    """Saves content to the specified file."""
    with open(path, 'w') as file:
        file.write(content)
    print(f"File generated and saved to '{path}'.")


def add_cuda_section(cuda_version: str, conda_env: str) -> str:
    """Generates the CUDA installation section."""
    return f"""
# Install CUDA
ARG CUDA_VERSION={cuda_version}
ENV CUDA_VERSION=${{CUDA_VERSION}}
RUN $CONDA_DIR/bin/conda install -n {conda_env} cuda -c nvidia/label/cuda-${{CUDA_VERSION}} -y && \
    $CONDA_DIR/bin/conda clean -afy
"""


def generate_dockerfile(
        dockerfile_path: str = "Dockerfile",
        ubuntu_version: str = "22.04",
        conda_version: str = "2023.07-0",
        conda_env: str = "py3.9",
        python_version: str = "3.9",
        jdk_version: str = "11",
        cuda_version: str = None,
) -> None:
    """
    Generates a Dockerfile based on the provided configurations.
    """
    base_dockerfile = f"""
# Base image
ARG UBUNTU_VERSION={ubuntu_version}
FROM ubuntu:${{UBUNTU_VERSION}}
# Non-interactive installation
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    wget curl git build-essential ca-certificates software-properties-common gnupg && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
# Install Anaconda
ARG CONDA_VERSION={conda_version}
ENV CONDA_DIR=/opt/conda
RUN wget -q https://repo.anaconda.com/archive/Anaconda3-${{CONDA_VERSION}}-Linux-x86_64.sh -O /tmp/anaconda.sh && \
    bash /tmp/anaconda.sh -b -p $CONDA_DIR && rm /tmp/anaconda.sh && $CONDA_DIR/bin/conda clean -afy
ENV PATH=$CONDA_DIR/bin:$PATH
RUN $CONDA_DIR/bin/conda init bash
# Conda setup
ARG CONDA_ENV={conda_env}
ARG PYTHON_VERSION={python_version}
RUN $CONDA_DIR/bin/conda create -n $CONDA_ENV python=${{PYTHON_VERSION}} -y && $CONDA_DIR/bin/conda clean -afy
RUN echo ". $CONDA_DIR/etc/profile.d/conda.sh" >> /etc/skel/.bashrc && echo "conda activate $CONDA_ENV" >> /etc/skel/.bashrc
# Install JDK within Conda
ARG JDK_VERSION={jdk_version}
RUN $CONDA_DIR/bin/conda install -n {conda_env} openjdk=${{JDK_VERSION}} -c conda-forge -y && $CONDA_DIR/bin/conda clean -afy
"""
    # Append CUDA section if specified
    if cuda_version:
        base_dockerfile += add_cuda_section(cuda_version, conda_env)

    # Add common configuration and default command
    base_dockerfile += f"""
# Create user and working directories
RUN useradd -ms /bin/bash docker && mkdir -p /workspace $CONDA_DIR/envs && chown -R docker:docker /workspace $CONDA_DIR/envs
USER docker
SHELL ["/bin/bash", "-c"]
WORKDIR /workspace
CMD ["/bin/bash"]
"""
    save_file(base_dockerfile, dockerfile_path)


def extract_services_from_yaml(config_path: str) -> dict:
    """Extracts services from a YAML configuration file."""
    try:
        with open(config_path, 'r') as yaml_file:
            config = yaml.safe_load(yaml_file)
            return config.get('services', {})
    except Exception as err:
        print(f"Error reading YAML configuration file: {err}")
        return {}


DOCKER_COMPOSE_VERSION = "3.8"
GPU_CAPABILITIES = "[gpu]"


def generate_base_compose(image_tag: str) -> str:
    """Generate the base docker-compose YAML for the app service."""
    return f"""version: '{DOCKER_COMPOSE_VERSION}'
services:
  app:
    image: {image_tag}
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: {GPU_CAPABILITIES}
    volumes:
      - ~/.ssh:/home/docker/.ssh
    command: /bin/bash -c "source ~/.bashrc && cd /workspace && /bin/bash"
"""


def collect_env_vars(services: dict) -> set:
    """Collect all environment variables across services."""
    global_env_vars = set()
    for service_name, config in services.items():
        if "environment" in config:
            global_env_vars.update(f"{k}={v}" for k, v in config["environment"].items())
    return global_env_vars


def generate_service_config(service_name: str, config: dict) -> str:
    """Generate docker-compose YAML for a specific service."""
    service_yml = f"  {service_name}:\n    image: {config.get('image', 'default:image')}\n"
    if "environment" in config:
        service_yml += "    environment:\n"
        service_yml += ''.join([f"      - {k}={v}\n" for k, v in config["environment"].items()])
    if "ports" in config:
        service_yml += "    ports:\n"
        service_yml += ''.join([f"      - \"{port}\"\n" for port in config["ports"]])
    if "restart" in config:
        service_yml += f"    restart: {config['restart']}\n"
    if "command" in config:
        service_yml += f"    command: {config['command']}\n"
    return service_yml


def generate_docker_compose_from_config(
        output_path: str, image_tag: str, config_path: str
) -> None:
    """
    Generates a docker-compose YAML file using provided Docker image tag and YAML configuration.
    Ensures all environment variables from other services are included in the app service.
    """
    # Generate base compose YAML for the app service
    base_compose = generate_base_compose(image_tag)

    # Extract services from YAML configuration
    services = extract_services_from_yaml(config_path)

    # Collect and add global environment variables to the app service
    global_env_vars = collect_env_vars(services)
    if global_env_vars:
        base_compose += "    environment:\n"
        base_compose += ''.join([f"      - {env_var}\n" for env_var in sorted(global_env_vars)])  # Sort for consistency

    # Add other services to the docker-compose YAML
    for service_name, config in services.items():
        base_compose += generate_service_config(service_name, config)

    # Save the generated docker-compose.yaml file
    save_file(base_compose, output_path)



def build_docker_image(image_tag: str, dockerfile_path: str = "Dockerfile") -> None:
    """Builds a Docker image with the specified tag."""
    try:
        subprocess.run(
            ["docker", "build", "-t", image_tag, "-f", dockerfile_path, "."],
            check=True,
        )
        print(f"Docker image built successfully with tag '{image_tag}'.")
    except subprocess.CalledProcessError as err:
        print(f"Error building Docker image: {err}")
        raise


def parse_arguments() -> argparse.Namespace:
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description="Dockerfile and Compose generator.")
    parser.add_argument("--dockerfile_path", default="Dockerfile", help="Path to save Dockerfile (default: Dockerfile)")
    parser.add_argument("--docker_image_tag", required=True, help="Tag for the Docker image")
    parser.add_argument("--compose_file_name", default="docker-compose.yaml", help="Name for the Docker Compose file")
    parser.add_argument("--ubuntu_version", default="22.04", help="Ubuntu version (default: 22.04)")
    parser.add_argument("--conda_env", default="py3.9", help="Name of the Conda environment (default: py3.9)")
    parser.add_argument("--conda_version", default="2023.07-0", help="Anaconda version (default: 2023.07-0)")
    parser.add_argument("--python_version", default="3.9", help="Python version (default: 3.9)")
    parser.add_argument("--jdk_version", default="11", help="JDK version (default: 11)")
    parser.add_argument("--cuda_version", default=None, help="CUDA version (optional, default: None)")
    parser.add_argument("--compose_config_path", default="docker_compose_config.yaml", help="Path to the YAML configuration file (default: config.yaml)")
    parser.add_argument("--create_compose", default=False, help="Create docker-compose.yaml file")
    parser.add_argument("--build_image", default=False, help="Build Docker image")


    return parser.parse_args()


def main() -> None:
    """Main function to parse arguments and generate the Dockerfile.

    Example usage:
        python create_docker_image.py --cuda_version 12.2 --redis_version latest \
        --mysql_password "admin" --compose_config_path config.yaml
        --mysql_password "admin"
    """
    args = parse_arguments()

    # Print parsed arguments with clear formatting
    print("\nParsed Arguments:\n" + "=" * 40)
    print(f"{'Argument':<20} {'Value':<20}")
    print("-" * 40)
    print(f"{'dockerfile_path:':<20} {args.dockerfile_path}")
    print(f"{'ubuntu_version:':<20} {args.ubuntu_version}")
    print(f"{'conda_version:':<20} {args.conda_version}")
    print(f"{'conda_env:':<20} {args.conda_env}")
    print(f"{'python_version:':<20} {args.python_version}")
    print(f"{'jdk_version:':<20} {args.jdk_version}")
    if args.cuda_version:
        print(f"{'cuda_version:':<20} {args.cuda_version}")
    print("=" * 40)
    generate_dockerfile(dockerfile_path=args.dockerfile_path ,
                        ubuntu_version =args.ubuntu_version,
                        conda_version=args.conda_version,
                        conda_env=args.conda_env,
                        python_version=args.python_version,
                        jdk_version=args.jdk_version,
                        cuda_version=args.cuda_version,)
    print("\nStep 1: Dockerfile generated.")

    if args.build_image:
        print("=" * 40)
        # Build Docker image
        build_docker_image(image_tag=str(args.docker_image_tag), dockerfile_path=args.dockerfile_path)
        print("=" * 40)
        print("\nStep 2: Docker image built.")

    # Generate docker-compose.yaml
    if args.create_compose:
        print("=" * 40)
        generate_docker_compose_from_config(
            output_path=args.compose_file_name,
            image_tag=args.docker_image_tag,
            config_path=args.compose_config_path
        )
        print("\nStep 3: docker-compose.yaml created.")


if __name__ == "__main__":
    main()


