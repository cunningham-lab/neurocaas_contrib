# set base image
FROM continuumio/anaconda3 

## Set shell:
#SHELL [ "/bin/bash", "--login", "-c" ]
RUN apt-get update
RUN apt-get install libffi-dev
RUN apt-get install -y vim
RUN apt-get -y install sudo

## Install pip
RUN conda install pip
RUN pip install --upgrade pip

# Create a non-root user
ARG username=neurocaasdev
ARG uid=1000
ARG gid=100
ENV USER $username
ENV UID $uid
ENV GID $gid
ENV HOME /home/$USER
RUN adduser --disabled-password \
    --gecos "Non-root user" \
    --uid $UID \
    --gid $GID \
    --home $HOME \
    $USER

RUN usermod -aG sudo $USER

ADD ./docker_setup/sudoers.txt /etc/sudoers
RUN chmod 440 /etc/sudoers

USER $USER

ENV CONDA_DIR /opt/conda 

# make non-activate conda commands available
ENV PATH=$CONDA_DIR/bin:$PATH
# make conda activate command available from /bin/bash --login shells
RUN echo ". $CONDA_DIR/etc/profile.d/conda.sh" >> ~/.profile
# make conda activate command available from /bin/bash --interative shells
RUN conda init bash

# set working directory
WORKDIR /home/$USER

#COPY ./ ./neurocaas_contrib/
RUN git clone https://github.com/cunningham-lab/neurocaas_contrib
# copy dependencies file to the working directory
COPY requirements.txt ./neurocaas_contrib/requirements.txt
# install dependencies
RUN pip install -r ./neurocaas_contrib/requirements.txt

COPY ./docker_setup/io-dir/ ./io-dir/

#RUN sudo chown -R $USER:$USER ./neurocaas_contrib
RUN sudo chown -R $USER:sudo ./io-dir

#COPY ./docker_setup/entrypoint.sh ./docker_setup/entrypoint.sh

#ENTRYPOINT [ "./docker_setup/entrypoint.sh" ]

CMD ["bash", "neurocaas_contrib/run_main.sh", "cianalysispermastack", "traviscipermagroup/inputs/dataset1.json", "results/", "traviscipermagroup/configs/config.json"]
