from setuptools import setup, find_packages

setup(
    name="dotmac-platform-sdk",
    version="1.0.0",
    description="Python SDK for DotMac Platform API",
    author="DotMac Platform Team",
    author_email="sdk@dotmac.com",
    url="https://github.com/dotmac/platform-sdk-python",
    packages=find_packages(),
    install_requires=[
        "httpx>=0.24.0",
        "pydantic>=2.0.0",
        "python-dateutil>=2.8.0",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
