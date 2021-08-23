from setuptools import setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(name='naspi',
      version='0.1.9',
      description='Simple NAS for Raspberry Pi',
      long_description=long_description,
      long_description_content_type='text/markdown',
      url='https://github.com/fgiroult321/simple-nas-pi',
      author='Frederic Giroult',
      author_email='frederic.giroult@gmail.com',
      license='MIT',
      packages=['naspi'],
      entry_points = {
        'console_scripts': ['naspi=naspi:main'],
        },
      classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
      ],
      python_requires='>=3.6',
      install_requires=[
        'boto3',
        'awscli'
      ],
      zip_safe=False)