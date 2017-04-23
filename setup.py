from setuptools import setup

setup(
    name='wah',
    packages=['wah'],
    include_package_data=True,
    install_requires=[
        'flask',
        'flask_sqlalchemy'
    ],
)
