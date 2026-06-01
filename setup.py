from setuptools import setup, find_packages

setup(
    name="sentinel-sd",
    version="3.2.4",
    description="Sentinel Security Kernel: Zero-Trust AI Firewall for Prompt Injection & Jailbreak Defense.",
    author="Sentinel Team",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "sentinel_shield": ["*.md", "*.json"],
    },
    install_requires=["sentence-transformers>=2.0.0"],
    entry_points={
        "console_scripts": [
            "sentinel-scan=sentinel_shield.core:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Security",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires='>=3.7',
)
