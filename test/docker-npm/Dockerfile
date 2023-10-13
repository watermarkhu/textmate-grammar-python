FROM debian:latest

# make working directory
RUN mkdir /node_root
WORKDIR /node_root 

# copy files 
COPY src/install.sh /node_root/install.sh
COPY src/entrypoint.sh /node_root/entrypoint.sh
COPY src/index.js /node_root/index.js

# execute install script
SHELL ["/bin/bash", "-c"]
RUN /node_root/install.sh

# run the app
CMD ["/node_root/entrypoint.sh"]
