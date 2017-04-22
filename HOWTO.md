# How to run a Flask application in Docker

Flask is a nice web application framework for Python.

My example `app.py` looks like:

```python
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello_world():
  return 'Hello, World!'
```

According to [Flask documentation](http://flask.pocoo.org/docs/0.12/quickstart/), to run the application we need to run `FLASK_APP=app.py flask run`. So our Dockerfile will run this command and we'll pass an environment variable with the application name when we start the container:

```
FROM python:3-onbuild
EXPOSE 5000
CMD [ "python", "-m", "flask", "run", "--host=0.0.0.0" ]
```

The `--host=0.0.0.0` parameter is necessary so that we will be able to connect to `flask` from outside the docker container.

Using the `-onbuild` version of the Python container is handy because it will import a file named `requirements.txt` and install the Python modules listed in it, so go on and create this file in the same directory, containing the single line, `flask`.

Now we can build our container:

```
docker build -t flaskapp .
```

This might take a while. When it ends, we'll be able to run the container, passing the `FLASK_APP` environment variable:

```
docker run -it --rm --name flaskapp \
  -v "$PWD":/usr/src/app -w /usr/src/app \
  -e LANG=C.UTF-8 -e FLASK_APP=app.py \
  -p 5000:5000 flaskapp
```

As you can see I'm mounting the local directory `$PWD` to `/usr/src/app` in the container and setting the work directory there. I'm also passing the `-p 5000:5000` parameter so that the container tcp port 5000 is available by connecting to my host machine port 5000.

You can test your app with your browser or with `curl`:

```
$ curl http://127.0.0.1:5000/
Hello, World!
```

I hope this will be useful to someone out there, have fun! :)
