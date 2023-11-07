FROM ubuntu:23.10
LABEL name="x-embed-tool"
LABEL description="A tool for generating text embeddings for X-Moderator in a qdrant vector-database."
LABEL maintainer="Anthony Waldsmith <awaldsmith@protonmail.com>"

# Install dependencies (libnvidia-gl-525-server)
RUN apt-get update -yq && apt-get install --no-install-recommends -yq git gcc g++ make cmake openssl curl zlib1g-dev python3-pip libvulkan-dev libvulkan1 vulkan-tools mesa-vulkan-drivers

# Install vulkan-sdk
RUN cd /tmp \
	&& curl -so - https://packages.lunarg.com/lunarg-signing-key-pub.asc | tee /etc/apt/trusted.gpg.d/lunarg.asc \
	&& curl -so /etc/apt/sources.list.d/lunarg-vulkan-jammy.list https://packages.lunarg.com/vulkan/lunarg-vulkan-jammy.list \
	&& apt update -yq \
	&& apt install -yq vulkan-sdk

ADD requirements.txt .
RUN pip install -r requirements.txt --break-system-packages

# Create user
RUN useradd -s /bin/bash -m xembedtool

WORKDIR /home/xembedtool

# Switch to user-mode
USER xembedtool

# Build pip dependences and install gpt4all for python
RUN echo "export PATH='${PATH}:~/.local/bin'" >> ~/.profile \
	&& . ~/.profile

ARG CMAKE_ARGS
ENV CMAKE_ARGS "${CMAKE_ARGS}"
RUN git clone --recurse-submodules https://github.com/nomic-ai/gpt4all \
	&& cd gpt4all/gpt4all-backend/ \
	&& mkdir build \
	&& cd build
RUN echo "CMAKE_ARGS=${CMAKE_ARGS:-}" \
	&& cd ~/gpt4all/gpt4all-backend/build \
	&& cmake .. ${CMAKE_ARGS} \
	&& cmake --build . --parallel --config Release \
	&& cd ../../gpt4all-bindings/python \
	&& pip install -e . --break-system-packages \
	&& cd ~/ \
	&& rm -rf gpt4all/

CMD python3 src/embed.py
