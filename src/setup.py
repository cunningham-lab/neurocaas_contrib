import setuptools

setuptools.setup(
    name="neurocaas_contrib", # Replace with your own username
    version="0.0.1",
    author="Taiga Abe",
    author_email="ta2507@columbia.com",
    description="Contribution package for the NeuroCAAS project",
    long_description="Package and repository for developers to build and contribute analyses to NeuroCAAS. Features tools for local build and testing via docker, and automatic deployment via pull requests.",
    long_description_content_type="text/markdown",
    url="https://github.com/cunningham-lab/neurocaas_contrib",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    python_requires='>=3.6.9',
    include_package_data=True,
    package_data={"":['docker_mats/*']}
)

