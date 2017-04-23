FROM python:3-onbuild
EXPOSE 5000
RUN pip install --editable .
CMD [ "python", "-m", "flask", "run", "--host=0.0.0.0" ]
