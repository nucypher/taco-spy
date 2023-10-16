FROM kprasch/rust-python:3.9.9
USER circleci

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . .

# Install any needed packages specified in requirements.txt
RUN sudo apt-get update && sudo apt-get install -y git python3-pip
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

# Run app.py when the container launches
CMD ["python3", "tacospy/main.py"]
