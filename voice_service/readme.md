# **KAVAS**

## Setup

1. Clone repo

```sh
git clone https://github.com/kidusshun/kavas
```

2. cd into project

```sh
cd KAVAS
```

3. create virtual environment

```sh
python -m venv venv
```

4. activate virtual environment

```sh
./venv/Scripts/activate
```

5. install dependencies

- Install FFmpeg (Linux)

```sh
# For Linux
sudo apt update
sudo apt install ffmpeg
```

- Install requirements

````

```sh
pip install -r requirements.txt
````

## Running application

```sh
uvicorn main:app --reload
```
