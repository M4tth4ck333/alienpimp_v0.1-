from setuptools import setup, find_packages

setup(
    name="alienmanager",
    version="0.1.0",
    author="M4tth4ck333",
    description="Modulares Framework zum Verwalten und Morphen von Security-Tool-Paketen mit TUI, Hashing und Versionierung",
    packages=find_packages(),
    install_requires=[
        "cmd2>=2.4.2",
        "rich>=13.0.0",
        "colorama>=0.4.6",
        "torch>=2.0.0",
        "sqlalchemy>=1.4",
        "pycryptodome>=3.17",
        "pyyaml>=6.0"
    ],
    python_requires='>=3.10',
    entry_points={
        "console_scripts": [
            "alienmgr=alienmanager.tui:main"
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3.10",
        "Operating System :: POSIX :: Linux",
        "License :: OSI Approved :: MIT License"
    ],
)
