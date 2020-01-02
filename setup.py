import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="polygon_client",
    version="1.0a4",
    author="Artem Tabolin",
    author_email="artemtab@gmail.com",
    description="Python wrapper for Polygon API (polygon.codeforces.com)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/citxx/polygon-py",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
