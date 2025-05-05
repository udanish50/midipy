from setuptools import setup, find_packages

setup(
    name="midipy",
    version="0.1.5",
    author="Muhammad Umair Danish",  # Replace with your actual name
    author_email="mdanish3@uwo.ca",
    description="A Python package for MIDI data processing, analysis, and parsing.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/udanish50/midipy",  # GitHub repo link
    packages=find_packages(include=["midipy", "midipy.*"]),
    install_requires=[
        "numpy",
        "pandas",
        "openpyxl",  # Required for saving to Excel
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Multimedia :: Sound/Audio :: MIDI",
    ],
    python_requires=">=3.6",
    license="MIT",
)
