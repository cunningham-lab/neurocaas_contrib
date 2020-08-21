import setuptools

with open("../README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="neurocaas_contrib", # Replace with your own username
    version="0.0.1",
    author="Taiga Abe",
    author_email="ta2507@columbia.com",
    description="Contribution package for the NeuroCAAS project",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cunningham-lab/neurocaas_contrib",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    python_requires='>=3.7',
)

