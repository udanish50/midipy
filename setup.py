from setuptools import setup, find_packages

setup(
    name="midipy",
    version="0.1.2",
    author="Your Name",
    author_email="mdanish3@uwo.ca",
    description="A Python package for MIDI data processing, analysis, and parsing.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/udanish50/midipy",  # Replace with your GitHub repo link
    packages=find_packages(),
    install_requires=[
        "numpy",
        "pandas",
        "openpyxl"  # Required for saving to Excel
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)

